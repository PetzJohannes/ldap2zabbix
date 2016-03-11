from pyzabbix import ZabbixAPI
from ldap3 import Connection

# Zabbix config
zabbixurl = ""
zabbixuser = "admin"
zabbixpass = ""
# Protect Zabbix users of deletion
sysusers = ["Admin", "guest"]
# LDAP config
ldapurl = ""
basedn = ""
delgroups = []
# LDAP groups to sync
groups = [
]

class LDAP(object):
    """
    LDAP connection class
    """
    def __init__(self, server, base):
        self.server = server
        self.base = base
        self.conn = Connection(self.server, auto_bind=True)

    def getGroup(self, groupname):
        self.conn.search('ou=People,' + self.base, '(&(objectclass=person)(memberof=cn=' + groupname + ',ou=Groups,' + self.base + '))', attributes=['uid', 'sn', 'givenName'])
        return self.conn.response

def defineGroupRights(accessgroups):
    for group in accessgroups[:]:
        hgroup = zapi.hostgroup.get(output=['name'], filter={'name': group['name']})
        accessgroups.remove(group)
        if hgroup:
            group['id'] = hgroup[0]['groupid']
        accessgroups.append(group)
    return accessgroups

def checkEqual(narray, zarray):
    """
    Check Zabbix user properties with LDAP user properties
    :param narray: LDAP properties array
    :param zarray: Zabbix properties array
    :return: True if LDAP properties are Zabbix properties
    """
    if len(narray) != len(zarray):
        return False
    for n in narray:
        found = False
        for z in zarray:
            if n == z:
                found = True
        if not found:
            return False
    return True

def checkGroup(groupname, accessgroups):
    """
    Get zabbix group if exists and create new if not
    :param groupname: LDAP groupname
    :return: Zabbix group
    """
    group = zapi.usergroup.get(output=['usrgrpid'], filter={'name': groupname}, selectRights="extend")
    rights = defineGroupRights(accessgroups)
    if not group:
        zgroup = zapi.usergroup.create(name=groupname, rights=rights)
        groupid = zgroup['usrgrpids'][0]
    else:
        groupid = group[0]['usrgrpid']
        # Check Zabbix equal rights is only possible with Zabbix version 3
        zabbixversion = zapi.apiinfo.version()[:1]
        if int(zabbixversion) < 3 or not checkEqual(rights, group[0]['rights']):
            zresponse = zapi.usergroup.update(usrgrpid=groupid, rights=rights)
    return groupid

def checkUserEqual(duser, zuser):
    """
    Check if two user are equal with given args
    :param duser: LDAP user
    :param zuser: Zabbix user
    :return: True if users are equal
    """
    equal = True
    for userval in duser:
        # Check user settings
        if userval == 'usrgrps':
            equal = checkEqual(duser[userval], zuser[userval])
        elif userval == "passwd":
            # Ignore password
            pass
        elif duser[userval] != zuser[userval]:
            equal = False
        else:
            # Pass all equal statements
            pass
        if not equal:
            # Drop for if one not equal value found
            return False
    return True

if __name__ == '__main__':
    # LDAP connection
    ldap = LDAP(ldapurl, basedn)
    # Zabbix connection
    zapi = ZabbixAPI(zabbixurl)
    zapi.session.verify = False
    zapi.login(zabbixuser, zabbixpass)

    # User done array
    dusers = {}

    # Start adding groups
    for group in groups:
        users = ldap.getGroup(group['name'])
        zgroupid = checkGroup(group['name'], group['rights'])
        for user in users:
            username = user['attributes']['uid'][0]
            surename = user['attributes']['sn'][0]
            name = user['attributes']['givenName'][0]
            grouptype = group['type']
            if username in dusers:
                dusers[username]['usrgrps'].append({'usrgrpid': zgroupid})
                if grouptype > int(dusers[username]['type']):
                    dusers[username]['type'] = str(grouptype)
            else:
                dusers[username] = {
                        'type': str(grouptype),
                        'usrgrps': [{'usrgrpid': zgroupid}],
                        'passwd': '',
                        'alias': username,
                        'surname': surename,
                        'name': name
                    }

    # Adding users
    for user in dusers:
        zuser = zapi.user.get(output="extend", selectUsrgrps=['usrgrpid'], filter={'alias': user})
        if zuser:
            dusers[user]['userid'] = zuser[0]['userid']
            if not checkUserEqual(dusers[user], zuser[0]):
                zresponse = zapi.user.update(dusers[user])
        else:
            zresponse = zapi.user.create(dusers[user])

    # Remove old users
    zusers = zapi.user.get(output=["alias"])
    for user in zusers:
        if user['alias'] not in dusers and user['alias'] not in sysusers:
            zresponse = zapi.user.delete(user['userid'])

    # Remove old groups
    for group in delgroups:
        group = zapi.usergroup.get(output=['name'], filter={'name': group})
        if group:
            zresponse = zapi.usergroup.delete(group[0]['usrgrpid'])
