"""Example: integrate Temporal Framework with Team B's org API via the adapter.

This is a minimal, non-destructive example that demonstrates how to fetch org
context from Team B and then (optionally) call the local policy engine.

Run with:
  python examples/integrate_with_team_b.py --email alice@example.com
"""
from __future__ import annotations

import argparse
import logging
import os
from pprint import pprint

from adapters.team_b_adapter import get_org_context, health_check

logger = logging.getLogger("integrate_with_team_b")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


def main(email: str) -> None:
    print("Checking Team B service health...")
    healthy = health_check()
    print("Team B healthy:" , healthy)

    print(f"Fetching org context for {email} from Team B...")
    try:
        ctx = get_org_context(email)
    except Exception as e:
        print("Failed to fetch org context:", e)
        return

    print("Org context received:")
    pprint(ctx)

    # Optional: Demonstrate integration point with our policy engine.
    # If you want to evaluate an access tuple using our engine, you can
    # create an EnhancedContextualIntegrityTuple from `core.tuples` and call
    # the policy engine. That code is intentionally left commented because
    # it depends on your local runtime wiring and configuration.

    # from core.tuples import EnhancedContextualIntegrityTuple, TemporalContext
    # from core.policy_engine import TemporalPolicyEngine

    # temporal_context = TemporalContext(service_id="example", user_id=email, location="unknown")
    # access_tuple = EnhancedContextualIntegrityTuple(
    #     data_type="employee_record",
    #     data_subject="employee_123",
    #     data_sender=email,
    #     data_recipient="hr_team",
    #     transmission_principle="business_need",
    #     temporal_context=temporal_context,
    # )
    # engine = TemporalPolicyEngine()
    # decision = engine.evaluate_request(access_tuple)
    # print('Decision:', decision)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Email address to query in Team B's API")
    args = parser.parse_args()
    main(args.email)
