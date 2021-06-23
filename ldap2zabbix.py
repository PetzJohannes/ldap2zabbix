import argparse
from Ldap import LDAP
import logging
import yaml
from Zabbix import Zabbix
from pyzabbix import ZabbixAPIException

if __name__ == '__main__':

    # arguments
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        "-c",
        help="Path to yaml configuration. Default: config.yaml",
        default='config.yaml'
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity. (Max: 2)",
        action="count",
        default=0
    )

    args = parser.parse_args()

    # setup logging
    if args.verbose >= 2:
        logging.basicConfig(level=logging.DEBUG)

    elif args.verbose == 1:
        logging.basicConfig(level=logging.INFO)

    # load configuration
    with open(args.config, 'r') as c:
        config = yaml.load(c, Loader=yaml.FullLoader)

    # set configuration options
    # Zabbix configuration
    zabbixUrl = config['zabbix']['url']

    zabbixUser = ''
    zabbixPassword = ''
    zabbixApiToken = None
    if 'user' in config['zabbix'] and 'password' in config['zabbix']:
        zabbixUser = config['zabbix']['user'] or ''
        zabbixPassword = config['zabbix']['password'] or ''

    elif 'token' in config['zabbix']:
        zabbixApiToken = config['zabbix']['token']
    else:
        print("Username and password or token not given in config.zabbix")
        exit(2)

    zabbixDefaultRole = config['zabbix']['default-role']
    zabbixDisabledGroup = config['zabbix'].get('disabled-group', 'Disabled-LDAP-Users')

    # LDAP configuration
    ldapUri = config['ldap']['uri']
    ldapBindUser = config['ldap'].get('bindUser')
    ldapBindPassword = config['ldap'].get('bindPassword')
    ldapObjectGroup = config['ldap'].get('objectGroup')
    ldapObjectUser = config['ldap'].get('objectUser')
    ldapAttributeMember = config['ldap'].get('attributeMember')
    ldapAttributeLastName = config['ldap'].get('attributeLastName')
    ldapAttributeFirstName = config['ldap'].get('attributeFirstName')
    ldapAttributeUsername = config['ldap'].get('attributeUsername')

    # sync configuration
    syncGroups = config['groups']

    # define LDAP
    ldap = LDAP(
        uri=ldapUri,
        bind_user=ldapBindUser,
        bind_password=ldapBindPassword,
        object_group=ldapObjectGroup,
        object_user=ldapObjectUser,
        attribute_member=ldapAttributeMember,
        attribute_last_name=ldapAttributeLastName,
        attribute_first_name=ldapAttributeFirstName,
        attribute_username=ldapAttributeUsername
    )

    # define Zabbix
    zabbix = Zabbix(
        url=zabbixUrl,
        user=zabbixUser,
        password=zabbixPassword,
        api_token=zabbixApiToken
    )

    users = {}

    # loop over configuration groups
    for group in syncGroups:

        # get group id
        z_group_id = zabbix.group_update_or_create(
            group['name'],
            group.get('permissions', [])
        )

        # Get ldap group members
        members = ldap.get_group_member(group['dn'])

        for member in members:

            # get the ldap user
            ldapUser = ldap.get_user(member)

            username = ldapUser['sAMAccountName']

            # if user is not in cache, add to cache
            if username not in users:
                users[username] = {
                    'username': username,
                    'name': ldapUser['givenName'],
                    'surname': ldapUser['sn'],
                    'usrgrps': [],
                    'roleid': zabbix.get_role_id(zabbixDefaultRole)
                }

            # add role to user (default if group role not present)
            if 'role' in group:
                users[username]['roleid'] = zabbix.get_role_id(group['role'])

            users[username]['usrgrps'].append({
                'usrgrpid': z_group_id
            })

    # Updating users
    for user in users:
        # create or update Zabbix users from LDAP
        zabbix.user_update_or_create(users[user])

    # remove users
    # get all Zabbix users
    z_users = zabbix.get_ldap_users()

    # check difference between Zabbix and actual LDAP users
    delete_users = [u['userid'] for u in z_users if u['username'] not in users]

    # delete users
    try:
        zabbix.delete_users(delete_users)

    except ZabbixAPIException as e:
        logging.error("Cannot delete Zabbix users.")
        logging.error(e.data)
        logging.error('Disabling those users.')
        logging.error('Resolve the displayed errors and delete the users manually or the next run will delete them.')

        logging.info('Creating disabled LDAP group.')

        # create or update disabled group
        z_disabled_group_id = zabbix.group_update_or_create(
            zabbixDisabledGroup,
            enabled=False
        )

        # disable users
        logging.info('Disabling users.')
        zabbix.disable_users(
            delete_users,
            z_disabled_group_id
        )

    # remove groups
    z_ldap_groups = zabbix.get_ldap_user_groups()
    configuredLdapGroupsByName = [g['name'] for g in syncGroups]

    # check difference between Zabbix and configured LDAP groups
    delete_groups = [g['usrgrpid'] for g in z_ldap_groups if g['name'] not in configuredLdapGroupsByName]

    # delete groups
    zabbix.delete_user_group(delete_groups)

    zabbix.logout()
