"""The provider-adapter add-on of the engine: adapters that speak to real model servers.

This package is deliberately not part of the engine's core module manifest. It is loaded the way
any third-party component package is loaded - by naming it in the ``external_modules`` list of the
engine configuration file (ADR 005) - so the plugin model carries its first real consumer instead
of being exercised only by test doubles. The core keeps the ``fake`` adapter and nothing else, and
this package keeps the provider semantics that would otherwise enter the core's release cadence:
endpoints, authentication, protocol drift. See ADR 014 §2.

Importing this package registers every adapter it ships. See ``example_config.json`` beside this
module for the configuration that reaches one.
"""

from workflow_engine_providers import lmstudio, ollama_systemone, openai_compatible
