from pathlib import Path
from pathlib import PurePath

from dynaconf import Dynaconf
from dynaconf.validator import Validator

CURRENT_DIRECTORY = Path().resolve()


def candore_settings(option_settings_file=None, option_components_file=None, conf_dir=None):
    settings_file = (
        PurePath(option_settings_file)
        if option_settings_file
        else PurePath(CURRENT_DIRECTORY, "settings.yaml")
    )
    components_file = (
        PurePath(option_components_file)
        if option_components_file
        else PurePath(CURRENT_DIRECTORY, "components.yaml")
    )
    if conf_dir:
        a_conf_dir = PurePath(conf_dir)
        if not Path(a_conf_dir).exists():
            raise OSError(f'The conf directory path {a_conf_dir} does not exists')
    else:
        a_conf_dir = PurePath('conf/')
    # Initialize and Configure Settings
    settings = Dynaconf(
        core_loaders=["YAML"],
        envvar_prefix="CANDORE",
        settings_files=[settings_file, components_file],
        preload=[f"{a_conf_dir}/*.yaml"],
        envless_mode=True,
        lowercase_read=True,
    )
    validate_settings(settings)
    return settings


def validate_settings(settings):
    provider_settings = [
        f"candore.{setting_key}" for setting_key in settings.to_dict().get("CANDORE")
    ]
    settings.validators.register(Validator(*provider_settings, ne=None))
    try:
        settings.validators.validate()
    except Exception as ecc:
        raise ecc
