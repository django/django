"""
Anonymous users
"""

class AnonymousUser:

    def __init__(self):
        pass

    def __repr__(self):
        return 'AnonymousUser'

    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def set_password(self, raw_password):
        raise NotImplementedError

    def check_password(self, raw_password):
        raise NotImplementedError

    def get_group_list(self):
        return []

    def set_groups(self, group_id_list):
        raise NotImplementedError

    def get_permission_list(self):
        return []

    def set_permissions(self, permission_id_list):
        raise NotImplementedError

    def has_perm(self, perm):
        return False

    def get_and_delete_messages(self):
        return []

    def add_session(self, session_md5, start_time):
        "Creates Session for this User, saves it, and returns the new object"
        raise NotImplementedError

    def is_anonymous(self):
        return True
