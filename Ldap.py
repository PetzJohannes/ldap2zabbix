from ldap3 import Connection, Server
import logging


class LDAP(object):
    """
    LDAP connection class
    """
    connection = None
    objectGroup = 'group'
    objectUser = 'person'
    attributeMember = 'member'
    attributeLastName = 'sn'
    attributeFirstName = 'givenName'
    attributeUsername = 'sAMAccountName'

    def __init__(
            self,
            uri,
            bind_user=None,
            bind_password=None
    ):
        server = Server(
            uri
        )

        self.connection = Connection(
            server,
            user=bind_user,
            password=bind_password,
            auto_bind=True,
            auto_referrals=False
        )

    def get_group(self, group_dn):
        self.connection.search(
            search_base=group_dn,
            search_filter=f"(objectClass={self.objectGroup})",
            search_scope='SUBTREE',
            attributes=['cn', self.attributeMember]
        )

        response = self.connection.response

        if len(response) > 1:
            raise Exception("Multiple groups found.")

        if len(response) == 0:
            logging.warning(f"Group '{group_dn}' not found.")
            return False

        return response[0]['attributes']

    def get_group_member(self, group_dn):

        group = self.get_group(group_dn)

        if not group:
            return []

        return group['member']

    def get_user(self, user_dn):
        self.connection.search(
            search_base=user_dn,
            search_filter=f"(objectClass={self.objectUser})",
            search_scope='SUBTREE',
            attributes=[
                self.attributeLastName,
                self.attributeFirstName,
                self.attributeUsername
            ]
        )

        response = self.connection.response

        if len(response) > 1:
            raise Exception("Multiple users found.")

        return response[0]['attributes']
