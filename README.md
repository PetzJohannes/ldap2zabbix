# LDAP user Zabbix sync
This script allows you to sync your LDAP users to Zabbix.

## Compatible Zabbix version
- 5.2

## Compatible LDAP Servers
- Microsoft Active Directory

## Features
- Sync given LDAP groups to Zabbix
- Sync LDAP users of given group to Zabbix
- Define permissions for LDAP groups
- Define tag permissions for LDAP groups
- Define user role
- Remove deleted LDAP users from Zabbix
- Remove no longer configured LDAP groups from Zabbix

## Requirements
- Python3 (`requirements.txt`)
- LDAP Surfer
- Zabbix API user with the permissions for
  * `Administration/User groups`
  * `Administration/User roles`
  * `Administration/Users`
  * `Access to API`

# How to
1. Copy the `config.example.yaml` to `config.yaml` or whatever you want.
    ```
    cp config.example.yaml config.yaml
    ```
2. Proceed with configuration
3. Run the sync
    ```
    python3 ldap2zabbix.py
    ```

> For more run `python3 ldap2zabbix.py -h`

## Zabbix configuration
```
zabbix:
  url: 
  user: 
  password: 
  default-role: 
```
| Setting        | Example value              | Description                                              |
|----------------|----------------------------|----------------------------------------------------------|
| url            | https://zabbix.com         | URL of your zabbix server                                |
| user           | zabbix-ldap-sync           | Zabbix API User                                          |
| password       | test                       | Zabbix API User password                                 |
| default-role   | ldap-user-role             | Default role for each user. Roles can be configured per group. See group configuration. |
| disabled-group | Disabled-LDAP-Users        | Default value: 'Disabled-LDAP-Users'.                    |

> If users are owners of Dashboards, Maps, etc. and cannot be deleted, the users will be disabled with the 
> `disabled-group` group.
> The `disabled-group` will be managed (created, updated) automatically!

## LDAP configuration
```
ldap:
  uri:
  bindUser:
  bindPassword:
```
| Setting      | Example value                | Description                                              |
|--------------|------------------------------|----------------------------------------------------------|
| uri          | ldaps://ldap.example.org:636 | Your LDAP(s) uri                                         |
| bindUser     | CN=surfer,DC=example,DC=org  | LDAP bind dn, default: ''                                |
| bindPassword | password                     | LDAP users password, default: ''                         |

## Group configuration
```
groups:
  - name: "user-group-from-ldap"
    dn: CN=Zabbix_Users,OU=Groups,DC=example,DC=com
    permissions:
      - group: Linux servers
        permission: read-only
        tags:
          - name: Mytag
            value: somevalue
```

For each group, you can define the following:

| Setting                | Example value                               | Required | Description                                                                                  |
|------------------------|---------------------------------------------|----------|----------------------------------------------------------------------------------------------|
| name                   | user-group-from-ldap                        | yes      | Zabbix group name                                                                            |
| dn                     | CN=Zabbix_Users,OU=Groups,DC=example,DC=org | yes      | LDAP bind dn                                                                                 |
| role                   | another zabbix role                         | no       | If you want to specify another role as the default role, configured in zabbix.default-role.  |
| permissions            |                                             | yes      | Array of permissions                                                                         |
| permissions.group      | Linux servers                               | yes      | Zabbix hostgroup name                                                                        |
| permissions.permission | read-only                                   | no       | Permission for the complete hostgroup. Allowed values: ['read-only', 'read-write', 'denied'] |
| permissions.tags       |                                             | no       | Array of tag permissions                                                                     |
| permissions.tags.name  | MYTAG                                       | no       | Tag name within the `group` to permit user action                                            |
| permissions.tags.value | somevalue                                   | no       | Tag value                                                                                    |

> Every user can have only one role. So the last specified role in the groups array is taken for this (or the default role).
> If you have multiple roles configured for groups a user is member, be aware that he will get the last configured one!

# Roadmap
- [ ] Support media types for users
