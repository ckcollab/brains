from importd import d

from submissions.models import Submission


##############################################################################
# Settings
d(
    INSTALLED_APPS=["participants", "submissions"],
    # mounts={
    #     "my_reusable_blog": "/blog/", # or /myblog/
    # }
)


##############################################################################
# Views
@d("/")
def index(request):
    return d.HttpResponse("Hello, I process submissions!")


@d("/submit/")
def submit(request):
    """Post data like

    name - Name of submitter
    submission - Zip file containing submission contents (this should have been signed by the client)
    """
    # They
    pass


if __name__ == "__main__":
    d.main()
