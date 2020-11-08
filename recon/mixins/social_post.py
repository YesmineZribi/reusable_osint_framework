from recon.core import framework

class SocialPost(framework.Framework):

    def __init__(self,post_id=None, author_id=None, text=None, created_at=None,is_reshared=False,
    reshared_on=None):
        framework.Framework.__init__(self, 'social_post')
        #Get seed info about user
        self.post_id = post_id
        self.author_id = author_id
        self.text = text
        self.created_at = created_at
        self.is_reshared = is_reshared
        self.reshared_on = reshared_on


    def get_post_id(self):
        return self.post_id

    def get_text(self):
        return self.text

    def __repr__(self):
        return f"Post({self.post_id},{self.author_id},{self.created_at})"
