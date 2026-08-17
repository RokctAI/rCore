# Intentionally empty module package.
#
# This exists (together with the 'paas' line in modules.txt) so that live
# sites migrating from the paas app keep a valid Module Def 'paas' row and
# do not fail migration on orphaned doctype/module references.
#
# TODO: remove this package and the 'paas' modules.txt line after the
# live-site data cleanup reassigns/removes the 'paas' Module Def.
