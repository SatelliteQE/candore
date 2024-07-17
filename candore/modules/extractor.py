import asyncio  # noqa: F401
import json
import math
import re
from functools import cached_property

import aiohttp

from candore.modules.ssh import Session

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
        self._api_endpoints = None
        self._completed_entities = []
        self._current_entity = None
        self._current_endpoint = None
        self._retry_limit = 3

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
        if not self._api_endpoints:
            self._api_endpoints = self.apilister.lister_endpoints()
        return self._api_endpoints

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
        if exc_val:
            with open("_partial_extraction.json", "w") as partial_file:
                json.dump(self._all_data, partial_file)
            with open("_resume_info.json", "w") as resume_file:
                json.dump(self.to_resume_dict(), resume_file, indent=4)

    async def _retry_get(self, retries=None, **get_params):
        if not retries:
            retries = self._retry_limit
        try:
            async with self.client.get(**get_params) as response:
                if response.status == 200:
                    json_data = await response.json()
                    return response.status, json_data
                else:
                    return response.status, {}
        except aiohttp.ClientError:
            if retries > 0:
                return await self._retry_get(retries=retries - 1, **get_params)
            else:
                print(
                    f"Failed to get data from {get_params.get('url')} "
                    f"in {self._retry_limit} retries."
                )
                raise

    async def paged_results(self, **get_params):
        status, _paged_results = await self._retry_get(**get_params, timeout=EXTENDED_TIMEOUT)
        if status == 200:
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
        status, results = await self._retry_get(**_request)
        if status == 200:
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
        endpoints = ['katello/api/activationkeys']
        """
        comp_data = []
        entities = None
        for endpoint in endpoints:
            self._current_endpoint = endpoint
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
        self._all_data = {}
        for component, endpoints in self.api_endpoints.items():
            self._current_entity = component
            if endpoints and component not in self._completed_entities:
                comp_entities = await self.process_entities(endpoints=endpoints)
                self._all_data[component] = comp_entities
            self._completed_entities.append(component)
        return self._all_data

    async def extract_all_rpms(self):
        """Extracts all installed RPMs from server"""
        with Session(settings=self.settings) as ssh_client:
            rpms = ssh_client.execute('rpm -qa').stdout
            rpms = rpms.splitlines()
            name_version_pattern = rf'{self.settings.rpms.regex_pattern}'
            rpms_matches = [re.compile(name_version_pattern).match(rpm) for rpm in rpms]
            rpms_list = [rpm_match.groups()[:-1] for rpm_match in rpms_matches if rpm_match]
            return dict(rpms_list)

    def to_resume_dict(self):
        """Exports our latest extraction progress information to a dictionary"""
        return {
            "api_endpoints": self._api_endpoints,
            "completed_entities": self._completed_entities,
            "current_entity": self._current_entity,
            "current_endpoint": self._current_endpoint,
        }

    def load_resume_info(self):
        """Resumes our extraction from the last known state"""
        with open("_resume_info.json") as resume_file:
            resume_info = json.load(resume_file)
        self._api_endpoints = resume_info["api_endpoints"]
        self._completed_entities = resume_info["completed_entities"]
        self._current_entity = resume_info["current_entity"]
        self._current_endpoint = resume_info["current_endpoint"]
