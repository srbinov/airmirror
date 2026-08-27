from mirror.identity import apply as _apply_identity

_apply_identity()

from mirror.app import main

if __name__ == "__main__":
    raise SystemExit(main())
