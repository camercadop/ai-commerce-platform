# Writing Logs

How to emit structured log output consistently across all modules.

See [ADR-005: Observability by Design](../adr/005-observability-by-design.md) and
[ADR-003: Security by Design](../adr/003-security-by-design.md) for the architectural rationale.

---

## 1. Declare a module-level logger

Every module that emits log output must declare a logger at the top of the file.

```python
import logging

logger = logging.getLogger(__name__)
```

## 2. Choose the correct log level

| Level | When to use |
| --- | --- |
| `logger.info` | Normal expected events (order created, payment succeeded) |
| `logger.warning` | Security-relevant or unexpected events (invalid token, rate limit hit) |
| `logger.error` | Unhandled exceptions and failures |

## 3. Use `%s`-style formatting

Never use f-strings in log calls. Use `%s`-style formatting so the string is only interpolated if the log level is active.

```python
# correct
logger.info("Order created: %s", order_id)

# wrong
logger.info(f"Order created: {order_id}")
```

## 4. Always log security enforcement decisions

Every security decision that denies access must produce a log entry.

```python
logger.warning("Login failed for user: %s", user_id)
logger.warning("Account locked: %s", user_id)
logger.warning("Permission denied: user=%s resource=%s", user_id, resource_id)
```

## 5. Never log sensitive data

The following must never appear in log output:

- Passwords
- Tokens or secrets
- Full request bodies
- Payment card data
- Personal identification data

```python
# correct
logger.info("Payment initiated: %s", payment_id)

# wrong
logger.info("Payment initiated with card: %s", card_number)
```

---

## Rules

- Every module that emits log output must declare a module-level logger using `logging.getLogger(__name__)`.
- Always use `%s`-style formatting — never f-strings in log calls.
- Always log security enforcement decisions: failed login, account locked, IP blocked, permission denied.
- Never log passwords, tokens, secrets, full request bodies, or sensitive personal data.
