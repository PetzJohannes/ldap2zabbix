from deepdiff import DeepDiff
import logging
from pyzabbix import ZabbixAPI


def resolve_permission(name):
    if name == 'denied':
        return '0'

    if name == 'read-only':
        return '2'

    if name == 'read-write':
        return '3'

    logging.error(f"Permission {name} not found.")
    logging.error("Possible permissions: 'denied', 'ready-only', 'read-write'.")
    raise Exception(f"Permission {name} not found.")


class Zabbix:
    zapi = None
    hostGroups = {}
    roles = {}

    def __init__(
            self,
            url,
            user,
            password
    ):
        self.zapi = ZabbixAPI(
            url,
            user=user,
            password=password
        )

    def get_host_group(self, name):

        # check in cache for host group id
        if name in self.hostGroups:
            return self.hostGroups[name]

        # resolve the Zabbix host group
        response = self.zapi.hostgroup.get(
            output=['groupid'],
            filter={
                'name': name
            }
        )

        if len(response) > 1:
            logging.error("Multiple Zabbix users found with same alias.")
            raise Exception("Multiple Zabbix users found.")

        if len(response) == 0:
            logging.info(f"No hostgroup fond for {name}.")
            return False

        return response[0]['groupid']

    def group_update_or_create(self, name, hostgroups=None, enabled=True):

        if hostgroups is None:
            hostgroups = []

        group = {
            'name': name,
            'users_status': '0' if enabled else '1',
            'gui_access': '2',
            'rights': [],
            'tag_filters': []
        }

        for hostgroup in hostgroups:

            z_group_id = self.get_host_group(hostgroup['group'])

            # only proceed if group exists
            if z_group_id:

                # check if we have group permissions
                if 'permission' in hostgroup:
                    # add group permissions
                    group['rights'].append({
                        'permission': resolve_permission(hostgroup['permission']),
                        'id': z_group_id
                    })

                # add tags for this group
                for tag in hostgroup['tags']:
                    group['tag_filters'].append({
                        'groupid': z_group_id,
                        'tag': tag['name'],
                        'value': tag['value']
                    })

        response = self.zapi.usergroup.get(
            output=['name', 'gui_access', 'users_status'],
            filter={
                'name': name
            },
            selectRights='extend',
            selectTagFilters='extend'
        )

        if len(response) > 1:
            logging.error("Multiple Zabbix users found with same alias.")
            raise Exception("Multiple Zabbix users found.")

        if len(response) == 0:
            # create user group
            return self.zapi.usergroup.create(
                **group
            )['usrgrpids'][0]

        # diff group
        z_group_data = response[0]

        # remove id from data
        z_group_id = z_group_data.pop('usrgrpid')

        diff = DeepDiff(
            z_group_data,
            group,
            ignore_order=True
        )

        # check if update required
        if diff:
            logging.info(f"Updating group {name} with id {z_group_id}.")

            # update group
            self.zapi.usergroup.update(
                usrgrpid=z_group_id,
                **group
            )

        return z_group_id

    def get_role_id(self, name):

        # check if already resolved
        if name in self.roles:
            return self.roles[name]

        response = self.zapi.role.get(
            output=['roleid'],
            filter={
                'name': name
            }
        )

        if len(response) > 1:
            logging.error("Multiple Zabbix roles found with same alias.")
            raise Exception("Multiple Zabbix roles found.")

        role_id = response[0]['roleid']

        self.roles[name] = role_id

        return role_id

    def user_update_or_create(
            self,
            user
    ):
        response = self.zapi.user.get(
            output=['userid', 'alias', 'name', 'surname', 'roleid'],
            selectUsrgrps=['usrgrpid'],
            filter={
                'alias': user['alias']
            }
        )

        if len(response) > 1:
            logging.error("Multiple Zabbix users found with same alias.")
            raise Exception("Multiple Zabbix users found.")

        if len(response) == 0:
            # create new user
            logging.info(f"Creating new User {user['alias']}")

            return self.zapi.user.create(
                **user
            )['userids'][0]

        # Diff old user
        z_user_data = response[0]
        z_user_id = z_user_data.pop('userid')

        diff = DeepDiff(
            z_user_data,
            user,
            ignore_order=True
        )

        # update Zabbix user
        if diff:
            logging.info(f"Updating user {user['alias']} with id {z_user_id}.")
            self.zapi.user.update(
                userid=z_user_id,
                **user
            )

        return z_user_id

    def get_ldap_user_groups(self):
        return self.zapi.usergroup.get(
            output='extend',
            filter={
                'gui_access': 2,
                'users_status': 0
            }
        )

    def delete_user_group(self, groups):

        # delete only if we have something to delete
        if not groups:
            return

        logging.info(f"Deleting Zabbix groups ({', '.join(groups)}).")
        self.zapi.do_request('usergroup.delete', params=groups)

    def get_ldap_users(self):

        # get all users because we cannot filter by gui_access flag.
        z_users = self.zapi.user.get(
            output=['userid', 'alias'],
            getAccess=True
        )

        # filter ldap users
        return [z_user for z_user in z_users if z_user['gui_access'] == "2"]

    def delete_users(self, users):

        # delete only if we have something to delete
        if not users:
            return

        logging.info(f"Deleting Zabbix users ({', '.join(users)}).")
        self.zapi.do_request('user.delete', params=users)

    def disable_users(self, users, disabled_group_id):

        # get old users of this group
        old_users = self.zapi.usergroup.get(
            output=['usrgrpid'],
            selectUsers=['userid'],
            usrgrpids=[disabled_group_id]
        )

        if old_users:

            old_user_ids = list(map(lambda u: u['userid'], old_users[0]['users']))

            # merge users with old users
            users += list(set(old_user_ids) - set(users))

        # update group with userids
        self.zapi.usergroup.update(
            usrgrpid=disabled_group_id,
            userids=users # list(map(lambda u: {'userid': u}, users))
        )

    def logout(self):
        """
        Logout from the Zabbix session.
        """
        response = self.zapi.user.logout()

        if not response:
            logging.debug("Zabbix logout failed.")
