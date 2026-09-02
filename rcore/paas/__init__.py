# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# Intentionally empty module package.
#
# This exists (together with the 'paas' line in modules.txt) so that live
# sites migrating from the paas app keep a valid Module Def 'paas' row and
# do not fail migration on orphaned doctype/module references.
#
# TODO: remove this package and the 'paas' modules.txt line after the
# live-site data cleanup reassigns/removes the 'paas' Module Def.
