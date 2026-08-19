# Re-export the user API surface at the package level. The manifest's
# whitelisted_methods aliases point at "rcore.users.api.user.<fn>"
# (no trailing ".user" module segment), so frappe.get_attr() resolves
# <fn> as an attribute of THIS package. An empty __init__ makes every
# alias raise AttributeError at dispatch. Same convention as the
# create_temporary_support_user/ and disable_temporary_support_user/
# package inits in this module.
from .user import *  # noqa: F401,F403
