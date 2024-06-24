import asyncio  # noqa: F401
import math
from functools import cached_property
from candore.modules.ssh import Session
import re
import aiohttp

# Max observed request duration in testing was approximately 888 seconds
# so we set the timeout to 2000 seconds to be overly safe
EXTENDED_TIMEOUT = aiohttp.ClientTimeout(total=2000, connect=60, sock_read=2000, sock_connect=60)


class Extractor:
    def __init__(self, settings, apilister=None):
        """Extract and save data using API lister endpoints

        :param apilister: APILister object
        """
        self.settings = settings
        self.username = self.settings.candore.username
        self._passwd = self.settings.candore.password
        self.base = self.settings.candore.base_url
        self.verify_ssl = False
        self.auth = aiohttp.BasicAuth(self.username, self._passwd)
        self.connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
        self.client = None
        self.apilister = apilister
        self.full = False
        self.semaphore = asyncio.Semaphore(self.settings.candore.max_connections)

    @cached_property
    def dependent_components(self):
        if hasattr(self.settings, "components"):
            return self.settings.components.dependencies

    @cached_property
    def ignore_components(self):
        if hasattr(self.settings, "components"):
            return self.settings.components.ignore

    @cached_property
    def api_endpoints(self):
        return self.apilister.lister_endpoints()

    async def _start_session(self):
        if not self.client:
            self.client = aiohttp.ClientSession(auth=self.auth, connector=self.connector)
        return self.client

    async def _end_session(self):
        await self.client.close()

    async def __aenter__(self):
        await self._start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._end_session()

    async def paged_results(self, **get_params):
        async with self.client.get(**get_params, timeout=EXTENDED_TIMEOUT) as response:
            if response.status == 200:
                _paged_results = await response.json()
                _paged_results = _paged_results.get("results")
                return _paged_results

    async def fetch_page(self, page, _request):
        async with self.semaphore:
            _request["params"].update({"page": page})
            page_entities = await self.paged_results(**_request)
            return page_entities

    async def fetch_all_pages(self, total_pages, _request, max_pages=None, skip_percent=None):
        if max_pages:
            stop = min(total_pages, max_pages)
        else:
            stop = total_pages
        if skip_percent:
            step = stop // math.ceil(stop * (100 - skip_percent) / 100)
        else:
            step = 1
        tasks = []
        print(f"Fetching {len(list(range(1, stop, step)))} more page(s).")
        for page in range(1, stop, step):
            task = asyncio.ensure_future(self.fetch_page(page, _request))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)
        return responses or []

    async def fetch_component_entities(self, **comp_params):
        entity_data = []
        endpoint = comp_params.get("endpoint", None)
        data = comp_params.get("data")
        dependency = comp_params.get("dependency", None)
        _request = {"url": self.base + "/" + endpoint, "params": {}}
        if data and dependency:
            _request["params"].update({f"{dependency}_id": data})
        async with self.client.get(**_request) as response:
            if response.status == 200:
                results = await response.json()
                if "results" in results:
                    entity_data.extend(results.get("results"))
                else:
                    # Return an empty directory for endpoints
                    # like services, api etc
                    # which does not have results
                    return entity_data
            else:
                return entity_data
        total_pages = results.get("total") // results.get("per_page") + 1
        if total_pages > 1:
            print(f"Endpoint {endpoint} has {total_pages} pages.")
            # If the entity has multiple pages, fetch them all
            if self.full:
                pages_data = await self.fetch_all_pages(total_pages, _request)
            elif self.max_pages or self.skip_percent:
                pages_data = await self.fetch_all_pages(
                    total_pages, _request, self.max_pages, self.skip_percent
                )
            else:
                return entity_data
            for page_entities in pages_data:
                if page_entities:
                    entity_data.extend(page_entities)
        return entity_data

    async def dependency_ids(self, dependency):
        # All the Ids of a specific dependency
        # e.g Organization IDs 1, 2, 3, 4
        endpoint = self.api_endpoints[f"{dependency}s"][0]
        depe_lists = await self.fetch_component_entities(endpoint=endpoint)
        depen_ids = [dep_dict["id"] for dep_dict in depe_lists]
        return depen_ids

    async def component_params(self, component_endpoint):
        """
        component_endpoints = ['katello/api/activationkeys']
        endpoints = ['activationkeys']
        :param component_endpoints:
        :return:
        """
        data = {}
        dependency = None
        # remove ignored endpoints
        _last = component_endpoint.rsplit("/")[-1]
        # Ignorable endpoint
        if self.ignore_components and _last in self.ignore_components:
            return
        # Return results for components those has dependencies
        if self.dependent_components and _last in self.dependent_components.keys():
            dependency = self.dependent_components[_last]
            data = await self.dependency_ids(dependency)
        return {"endpoint": component_endpoint, "data": data, "dependency": dependency}

    async def process_entities(self, endpoints):
        """
        endpoints = ['katello/api/actiovationkeys']
        """
        comp_data = []
        entities = None
        for endpoint in endpoints:
            comp_params = await self.component_params(component_endpoint=endpoint)
            if comp_params:
                entities = []
                if isinstance(comp_params.get("data"), list):
                    for data_point in comp_params.get("data"):
                        depen_data = await self.fetch_component_entities(
                            endpoint=comp_params["endpoint"],
                            dependency=comp_params.get("dependency"),
                            data=data_point,
                        )
                        if not depen_data:
                            continue
                        entities.extend(depen_data)
                else:
                    entities = await self.fetch_component_entities(**comp_params)
            if entities:
                comp_data.extend(entities)
        return comp_data

    async def extract_all_entities(self):
        """Extract all entities fom all endpoints

        :return:
        """
        all_data = {}
        for component, endpoints in self.api_endpoints.items():
            if endpoints:
                comp_entities = await self.process_entities(endpoints=endpoints)
                all_data[component] = comp_entities
        return all_data

    async def extract_all_rpms(self):
        """Extracts all installed RPMs from server"""
        with Session() as ssh_client:
            rpms = ssh_client.execute('rpm -qa').stdout
            rpms = rpms.splitlines()
            name_version_pattern = rf'{self.settings.rpms.regex_pattern}'
            rpms_matches = [
                re.compile(name_version_pattern).match(rpm) for rpm in rpms
            ]
            rpms_list = [rpm_match.groups()[:-1] for rpm_match in rpms_matches if rpm_match]
            return dict(rpms_list)
