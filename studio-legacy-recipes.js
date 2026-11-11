// Imported from the continuous player's 45 saved recipes.
const legacyStudioRecipes = [
  {
    "title": "Pure White Noise",
    "group": "sleep",
    "tracks": [
      {
        "asset": 15,
        "start": 0,
        "gain": 0.8,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Gentle White Noise",
    "group": "sleep",
    "tracks": [
      {
        "asset": 21,
        "start": 0,
        "gain": 0.8,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Deep Brown Noise",
    "group": "sleep",
    "tracks": [
      {
        "asset": 22,
        "start": 0,
        "gain": 0.8,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Pink Noise for Focus",
    "group": "focus",
    "tracks": [
      {
        "asset": 16,
        "start": 0,
        "gain": 0.8,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Warm Pink Study",
    "group": "focus",
    "tracks": [
      {
        "asset": 23,
        "start": 0,
        "gain": 0.8,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Neutral Masking",
    "group": "focus",
    "tracks": [
      {
        "asset": 24,
        "start": 0,
        "gain": 0.8,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Soft Night Sound",
    "group": "sleep",
    "tracks": [
      {
        "asset": 21,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 22,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Blanket Noise",
    "group": "sleep",
    "tracks": [
      {
        "asset": 17,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 16,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Deep Room Noise",
    "group": "sleep",
    "tracks": [
      {
        "asset": 34,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 17,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Faint Fan",
    "group": "sleep",
    "tracks": [
      {
        "asset": 25,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 21,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Box Fan Overnight",
    "group": "sleep",
    "tracks": [
      {
        "asset": 26,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 16,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Air Conditioner Room",
    "group": "sleep",
    "tracks": [
      {
        "asset": 33,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 16,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Airplane Seat Hum",
    "group": "travel",
    "tracks": [
      {
        "asset": 32,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 22,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "White Noise Black Screen",
    "group": "sleep",
    "tracks": [
      {
        "asset": 15,
        "start": 0,
        "gain": 0.8,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Brown Noise Black Screen",
    "group": "sleep",
    "tracks": [
      {
        "asset": 17,
        "start": 0,
        "gain": 0.8,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Steady Office",
    "group": "focus",
    "tracks": [
      {
        "asset": 25,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 24,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Continuous Focus",
    "group": "focus",
    "tracks": [
      {
        "asset": 23,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 21,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Dark Focus",
    "group": "focus",
    "tracks": [
      {
        "asset": 22,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 23,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Gentle Wind",
    "group": "relax",
    "tracks": [
      {
        "asset": 31,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 16,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Night Wind",
    "group": "sleep",
    "tracks": [
      {
        "asset": 31,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 34,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Rainy Room",
    "group": "sleep",
    "tracks": [
      {
        "asset": 6,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 23,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Deep Rain",
    "group": "sleep",
    "tracks": [
      {
        "asset": 27,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 17,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Rain and Fan",
    "group": "sleep",
    "tracks": [
      {
        "asset": 6,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 25,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Ocean and Brown",
    "group": "sleep",
    "tracks": [
      {
        "asset": 28,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 22,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Ocean and Wind",
    "group": "relax",
    "tracks": [
      {
        "asset": 28,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 31,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Waterfall Wash",
    "group": "focus",
    "tracks": [
      {
        "asset": 29,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 16,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Shower and Fan",
    "group": "relax",
    "tracks": [
      {
        "asset": 30,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 26,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Cloudy Morning",
    "group": "focus",
    "tracks": [
      {
        "asset": 6,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 21,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Muted Rain",
    "group": "sleep",
    "tracks": [
      {
        "asset": 6,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 22,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Very Soft Rain",
    "group": "sleep",
    "tracks": [
      {
        "asset": 6,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 21,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Quiet Cabin",
    "group": "travel",
    "tracks": [
      {
        "asset": 32,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 16,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Distant Rumble",
    "group": "sleep",
    "tracks": [
      {
        "asset": 34,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 31,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Gentle Focus Room",
    "group": "focus",
    "tracks": [
      {
        "asset": 24,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 33,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Air and Water",
    "group": "relax",
    "tracks": [
      {
        "asset": 31,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 29,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Steady Hum",
    "group": "focus",
    "tracks": [
      {
        "asset": 33,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 26,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Soft Pink Masking",
    "group": "focus",
    "tracks": [
      {
        "asset": 16,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 23,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "White and Brown",
    "group": "sleep",
    "tracks": [
      {
        "asset": 15,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 17,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Midnight Cabin",
    "group": "sleep",
    "tracks": [
      {
        "asset": 32,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 31,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Sleep Fan with Rain",
    "group": "sleep",
    "tracks": [
      {
        "asset": 26,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 6,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Soft Noise for Study",
    "group": "focus",
    "tracks": [
      {
        "asset": 21,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 16,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Ocean Focus",
    "group": "focus",
    "tracks": [
      {
        "asset": 28,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 24,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Rain Window Concept",
    "group": "sleep",
    "tracks": [
      {
        "asset": 6,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 31,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Calm Deep Space",
    "group": "focus",
    "tracks": [
      {
        "asset": 34,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 23,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Private Fan Room",
    "group": "sleep",
    "tracks": [
      {
        "asset": 25,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 17,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  },
  {
    "title": "Balanced Deep Noise",
    "group": "sleep",
    "tracks": [
      {
        "asset": 16,
        "start": 0,
        "gain": 0.6,
        "loop": true,
        "mute": false
      },
      {
        "asset": 17,
        "start": 0,
        "gain": 0.25,
        "loop": true,
        "mute": false
      }
    ]
  }
];
