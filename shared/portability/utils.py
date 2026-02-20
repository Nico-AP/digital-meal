from shared.portability.constants import PortabilityContexts


def get_request_context(request) -> str:
    # TODO: Adjust when My DM is moved to subdomain
    if request.path.startswith("/my/"):
        return PortabilityContexts.MY_DM
    else:
        return PortabilityContexts.DM_EDU
