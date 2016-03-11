# LDAP user Zabbix sync
This script allows you to sync your LDAP users to Zabbix.

## Features
- Sync given LDAP groups to Zabbix
- Sync LDAP users of given group to Zabbix
- Define permissions for LDAP groups and LDAP users
- Delete given LDAP groups and LDAP users in this groups in Zabbix
- Zabbix version >= 3: Update usergroups only if changes are found

## Requirements
- pyzabbix
- ldap3
- python3.4

## Tested Zabbix version
- 2.4
- 3.0

# Configuration
Open the ldap2zabbix.py.

| Setting    | Default value              | Description                                              |
|------------|----------------------------|----------------------------------------------------------|
| zabbixurl  | https://zabbix.example.org | Zabbix web url                                           |
| zabbixuser | admin                      | Should be an internal admin                              |
| zabbixpass |                            | Users password                                           |
| sysusers   | ["Admin", "guest"]         | Array of internal users. Will be protected from deletion |
| ldapurl    | ldap://ldap.example.org    | Your LDAP(s) url                                         |
| basedn     | dc=example,dc=org          | Your LDAP base dn                                        |
| groups     | [ ]                        | LDAP groups to sync (See below)                          |
| delgroups  | [ ]                        | LDAP groups to delete in Zabbix                          |

## Delgroups
Example:
```python
delgroups = ["firstgroup", "secondgroup"]
```
All given groups will be deleted.

## Deleteusers
All users without LDAP groups and not in "sysusers" will be deleted.

## Groups
| Setting | Description                          |
|---------|--------------------------------------|
| name    | LDAP group name                      |
| type    | Zabbix user access type (see below)  |
| rights  | Zabbix group permissions (see below) |
Example:
```python
groups = [
    {
        'name': 'superadmingroup',
        'type': 3,
        'rights': [
        ]
    },
    {
        'name': 'admingroup',
        'type': 2,
        'rights': [
            {
                'permission': 3,
                'name': 'Linux server'
            },
            {
                'permission': 3,
                'name': 'Windows server'
            }
        ]
    },
    {
        'name': 'viewergroup',
        'type': 1,
        'rights': [
            {
                'permission': 2,
                'name': 'Linux server'
            }
        ]
    }
]
```
This example syncs all members of "superadmingroup", "admingroup" and "viewergroup" to Zabbix.

### Type
| Type | Description             |
|------|-------------------------|
| 1    | (Default) User          |
| 2    | Zabbix Admin User       |
| 3    | Zabbix Super Admin User |

[Zabbix API User object docu](https://www.zabbix.com/documentation/2.4/manual/api/reference/user/object#user)

[Zabbix Permission docu](https://www.zabbix.com/documentation/2.4/manual/config/users_and_usergroups/permissions)

### Rights
A dict with Zabbix "host group" element names and permissions. Multiple groups can be defined

| Permission | Description       |
|------------|-------------------|
| 0          | access denied     |
| 2          | read-only access  |
| 3          | read-write access |

[Zabbix API User group object docu](https://www.zabbix.com/documentation/2.4/manual/api/reference/usergroup/object#permission)

# Roadmap
- [ ] Support media types for users
