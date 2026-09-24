"""Entry point of the admin panel."""

from craft.http.controller import Controller
from craft.http.response import redirect


class HomeController(Controller):
    """Sends `/admin` to the first screen of the panel."""

    def admin(self, request):
        """Redirect `/admin` to role management, the core of the panel.

        The route carries `auth` and `role:admin`, so an account without the
        role is refused before it reaches this redirect.
        """
        return redirect(route="admin.roles.index")
