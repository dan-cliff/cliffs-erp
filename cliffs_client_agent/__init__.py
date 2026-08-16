from . import models
from . import controllers

from .provisioning import create_system_manager


def _create_system_manager(env):
    create_system_manager(env)
