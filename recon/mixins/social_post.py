from recon.core import framework

class SocialPost(framework.Framework):

    def __init__(self,post_id=None, author=None, text=None, created_at=None):
        framework.Framework.__init__(self, 'social_post')
        #Get seed info about user
        self.post_id = post_id
        self.author = author
        self.text = text
        self.created_at = created_at


    def get_post_id(self):
        return self.post_id

    def get_text(self):
        return self.text

    def __repr__(self):
        return f"Post({self.post_id},{self.author_id},{self.created_at})"

class Reshare(framework.Framework):
    def __init__(self, resharer=None,reshared_post=None,original_post=None):
        """
        resharer: SocialUser
        reshared_post: Post
        original_post: Post
        """
        framework.Framework.__init__(self, 'social_post')
        self.resharer = resharer
        self.reshared_post = reshared_post
        self.original_post = original_post

class Mention(framework.Framework):
    def __init__(self, mentioner=None,mentioned=None,post=None):
        """
        mentioner: SocialUser
        mentioned: SocialUser
        original_post: Post
        """
        framework.Framework.__init__(self, 'social_post')
        self.mentioner = mentioner
        self.mentioned = mentioned
        self.post = post


class Comment(framework.Framework):
    def __init__(self, author=None,post=None):
        """
        author: SocialUser
        post: Post
        """
        framework.Framework.__init__(self, 'social_post')
        self.author = author
        self.post = post
