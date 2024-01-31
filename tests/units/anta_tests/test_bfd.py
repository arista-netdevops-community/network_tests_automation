# Copyright (c) 2023-2024 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Tests for anta.tests.bfd.py
"""
# pylint: disable=C0302
from __future__ import annotations

from typing import Any

# pylint: disable=C0413
# because of the patch above
from anta.tests.bfd import VerifyBFDPeersHealth  # noqa: E402
from tests.lib.anta import test  # noqa: F401; pylint: disable=W0611

DATA: list[dict[str, Any]] = [
    {
        "name": "success",
        "test": VerifyBFDPeersHealth,
        "eos_data": [
            {
                "vrfs": {
                    "default": {
                        "ipv4Neighbors": {
                            "192.0.255.7": {
                                "peerStats": {
                                    "": {
                                        "status": "up",
                                        "remoteDisc": 3940685114,
                                        "lastDown": 1703657258.652725,
                                        "l3intf": "",
                                    }
                                }
                            },
                        },
                        "ipv6Neighbors": {},
                    },
                    "MGMT": {
                        "ipv4Neighbors": {
                            "192.0.255.71": {
                                "peerStats": {
                                    "": {
                                        "status": "up",
                                        "remoteDisc": 3940685114,
                                        "lastDown": 1703657258.652725,
                                        "l3intf": "",
                                    }
                                }
                            },
                        },
                        "ipv6Neighbors": {},
                    },
                }
            },
            {
                "utcTime": 1703658481.8778424,
            },
        ],
        "inputs": {"down_threshold": 2},
        "expected": {"result": "success"},
    },
    {
        "name": "failure-no-peer",
        "test": VerifyBFDPeersHealth,
        "eos_data": [
            {
                "vrfs": {
                    "MGMT": {
                        "ipv6Neighbors": {},
                        "ipv4Neighbors": {},
                    },
                    "default": {
                        "ipv6Neighbors": {},
                        "ipv4Neighbors": {},
                    },
                }
            },
            {
                "utcTime": 1703658481.8778424,
            },
        ],
        "inputs": None,
        "expected": {
            "result": "failure",
            "messages": ["No IPv4 BFD peers are configured for any VRF."],
        },
    },
    {
        "name": "failure-session-down",
        "test": VerifyBFDPeersHealth,
        "eos_data": [
            {
                "vrfs": {
                    "default": {
                        "ipv4Neighbors": {
                            "192.0.255.7": {
                                "peerStats": {
                                    "": {
                                        "status": "down",
                                        "remoteDisc": 0,
                                        "lastDown": 1703657258.652725,
                                        "l3intf": "",
                                    }
                                }
                            },
                            "192.0.255.70": {
                                "peerStats": {
                                    "": {
                                        "status": "up",
                                        "remoteDisc": 3940685114,
                                        "lastDown": 1703657258.652725,
                                        "l3intf": "",
                                    }
                                }
                            },
                        },
                        "ipv6Neighbors": {},
                    },
                    "MGMT": {
                        "ipv4Neighbors": {
                            "192.0.255.71": {
                                "peerStats": {
                                    "": {
                                        "status": "down",
                                        "remoteDisc": 0,
                                        "lastDown": 1703657258.652725,
                                        "l3intf": "",
                                    }
                                }
                            },
                        },
                        "ipv6Neighbors": {},
                    },
                }
            },
            {
                "utcTime": 1703658481.8778424,
            },
        ],
        "inputs": {"down_threshold": 2},
        "expected": {
            "result": "failure",
            "messages": [
                "Following BFD peers are not up:\n192.0.255.7 is down in default VRF with remote disc 0.\n192.0.255.71 is down in MGMT VRF with remote disc 0."
            ],
        },
    },
    {
        "name": "failure-session-up-disc",
        "test": VerifyBFDPeersHealth,
        "eos_data": [
            {
                "vrfs": {
                    "default": {
                        "ipv4Neighbors": {
                            "192.0.255.7": {
                                "peerStats": {
                                    "": {
                                        "status": "up",
                                        "remoteDisc": 0,
                                        "lastDown": 1703657258.652725,
                                        "l3intf": "Ethernet2",
                                    }
                                }
                            },
                            "192.0.255.71": {
                                "peerStats": {
                                    "": {
                                        "status": "up",
                                        "remoteDisc": 0,
                                        "lastDown": 1703657258.652725,
                                        "l3intf": "Ethernet2",
                                    }
                                }
                            },
                        },
                        "ipv6Neighbors": {},
                    }
                }
            },
            {
                "utcTime": 1703658481.8778424,
            },
        ],
        "inputs": {},
        "expected": {
            "result": "failure",
            "messages": ["Following BFD peers were down:\n 192.0.255.7 in default VRF has remote disc 0.\n 192.0.255.71 in default VRF has remote disc 0."],
        },
    },
    {
        "name": "failure-last-down",
        "test": VerifyBFDPeersHealth,
        "eos_data": [
            {
                "vrfs": {
                    "default": {
                        "ipv4Neighbors": {
                            "192.0.255.7": {
                                "peerStats": {
                                    "": {
                                        "status": "up",
                                        "remoteDisc": 3940685114,
                                        "lastDown": 1703657258.652725,
                                        "l3intf": "",
                                    }
                                }
                            },
                            "192.0.255.71": {
                                "peerStats": {
                                    "": {
                                        "status": "up",
                                        "remoteDisc": 3940685114,
                                        "lastDown": 1703657258.652725,
                                        "l3intf": "",
                                    }
                                }
                            },
                            "192.0.255.17": {
                                "peerStats": {
                                    "": {
                                        "status": "up",
                                        "remoteDisc": 3940685114,
                                        "lastDown": 1703657258.652725,
                                        "l3intf": "",
                                    }
                                }
                            },
                        },
                        "ipv6Neighbors": {},
                    }
                }
            },
            {
                "utcTime": 1703667348.111288,
            },
        ],
        "inputs": {"down_threshold": 2},
        "expected": {
            "result": "failure",
            "messages": [
                "Following BFD peers were down:\n192.0.255.7 in default VRF was down 3 hours ago.\n"
                "192.0.255.71 in default VRF was down 3 hours ago.\n192.0.255.17 in default VRF was down 3 hours ago."
            ],
        },
    },
]