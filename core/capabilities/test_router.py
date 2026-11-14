from core.capabilities.router import route_capabilities
from core.capabilities.status import capability_state


tests = [
    "Build a nicer dashboard for Jarvis",
    "Debug this Python service",
    "Research the latest AI coding tools",
    "Create pricing and SEO strategy for the product",
    "Review the architecture of the agent runtime",
]

for prompt in tests:
    result = route_capabilities(prompt)

    print()
    print(prompt)
    print("domain:", result.domain)
    print("reason:", result.reason)

    for name in result.capabilities:
        print(f"  {name}: {capability_state(name)}")
