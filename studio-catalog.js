// Append-only order preserves numeric asset IDs in shared Studio projects.
const studioPublishedAssets = [
  {
    "name": "Tiếng ồn trắng",
    "key": "audio/white-noise.mp3",
    "group": "noise",
    "aliases": "White Noise",
    "source": "/sounds/white-noise/",
    "duration": 600.033
  },
  {
    "name": "Tiếng ồn hồng",
    "key": "audio/pink-noise.mp3",
    "group": "noise",
    "aliases": "Pink Noise",
    "source": "/sounds/pink-noise/",
    "duration": 600.033
  },
  {
    "name": "Tiếng ồn nâu",
    "key": "audio/brown-noise.mp3",
    "group": "noise",
    "aliases": "Brown Noise",
    "source": "/sounds/brown-noise/",
    "duration": 600.033
  },
  {
    "name": "Tiếng ồn xanh lá",
    "key": "audio/green-noise.mp3",
    "group": "noise",
    "aliases": "Green Noise",
    "source": "/sounds/green-noise/",
    "duration": 600.033
  },
  {
    "name": "Tiếng ồn xanh dương",
    "key": "audio/blue-noise.mp3",
    "group": "noise",
    "aliases": "Blue Noise",
    "source": "/sounds/blue-noise/",
    "duration": 600.033
  },
  {
    "name": "Tiếng ồn tím",
    "key": "audio/violet-noise.mp3",
    "group": "noise",
    "aliases": "Violet Noise",
    "source": "/sounds/violet-noise/",
    "duration": 600.033
  },
  {
    "name": "Tiếng ồn trắng dịu",
    "key": "audio/soft-white-noise.mp3",
    "group": "noise",
    "aliases": "Soft White Noise",
    "source": "/sounds/soft-white-noise/",
    "duration": 600.033
  },
  {
    "name": "Tiếng ồn nâu trầm",
    "key": "audio/deep-brown-noise.mp3",
    "group": "noise",
    "aliases": "Deep Brown Noise",
    "source": "/sounds/deep-brown-noise/",
    "duration": 600.033
  },
  {
    "name": "Tiếng ồn hồng ấm",
    "key": "audio/warm-pink-noise.mp3",
    "group": "noise",
    "aliases": "Warm Pink Noise",
    "source": "/sounds/warm-pink-noise/",
    "duration": 600.033
  },
  {
    "name": "Tiếng ồn dải trung",
    "key": "audio/mid-noise.mp3",
    "group": "noise",
    "aliases": "Neutral Mid Noise",
    "source": "/sounds/neutral-mid-noise/",
    "duration": 600.033
  },
  {
    "name": "Quạt bàn",
    "key": "audio/desk-fan-synth.mp3",
    "group": "fan",
    "aliases": "Desk Fan — Synthetic",
    "source": "/sounds/desk-fan/",
    "duration": 600.033
  },
  {
    "name": "Quạt hộp",
    "key": "audio/box-fan-real.mp3",
    "group": "fan",
    "aliases": "Box Fan — Field Recording",
    "source": "/sounds/box-fan/",
    "duration": 67.553
  },
  {
    "name": "Mưa lớn",
    "key": "audio/heavy-rain-real.mp3",
    "group": "rain",
    "aliases": "Heavy Rain",
    "source": "/sounds/heavy-rain/",
    "duration": 189.806
  },
  {
    "name": "Sóng biển",
    "key": "audio/ocean-waves-real.mp3",
    "group": "water",
    "aliases": "Ocean Waves",
    "source": "/sounds/ocean-waves/",
    "duration": 89.861
  },
  {
    "name": "Thác nước",
    "key": "audio/waterfall-real.mp3",
    "group": "water",
    "aliases": "Waterfall",
    "source": "/sounds/waterfall/",
    "duration": 375.51
  },
  {
    "name": "Vòi sen",
    "key": "audio/shower-synth.mp3",
    "group": "water",
    "aliases": "Shower — Synthetic",
    "source": "/sounds/shower/",
    "duration": 600.033
  },
  {
    "name": "Gió nhẹ",
    "key": "audio/wind-synth.mp3",
    "group": "wind",
    "aliases": "Gentle Wind — Synthetic",
    "source": "/sounds/gentle-wind/",
    "duration": 600.033
  },
  {
    "name": "Khoang máy bay",
    "key": "audio/cabin-hum-synth.mp3",
    "group": "transit",
    "aliases": "Airplane Cabin — Synthetic",
    "source": "/sounds/airplane-cabin/",
    "duration": 600.033
  },
  {
    "name": "Máy điều hòa",
    "key": "audio/air-conditioner-synth.mp3",
    "group": "fan",
    "aliases": "Air Conditioner — Synthetic",
    "source": "/sounds/air-conditioner/",
    "duration": 600.033
  },
  {
    "name": "Tiếng rung trầm",
    "key": "audio/low-rumble.mp3",
    "group": "hum",
    "aliases": "Low Rumble",
    "source": "/sounds/low-rumble/",
    "duration": 600.033
  },
  {
    "name": "Mưa nhẹ",
    "key": "audio/light-rain-real.mp3",
    "group": "rain",
    "aliases": "Light Rain",
    "source": "/sounds/light-rain/",
    "duration": 600.033
  },
  {
    "name": "Mưa trên lều",
    "key": "audio/rain-on-tent-real.mp3",
    "group": "rain",
    "aliases": "Rain on Tent",
    "source": "/sounds/rain-on-tent/",
    "duration": 600.033
  },
  {
    "name": "Mưa trên nóc ô tô",
    "key": "audio/rain-car-roof-real.mp3",
    "group": "rain",
    "aliases": "Rain on Car Roof",
    "source": "/sounds/rain-on-car-roof/",
    "duration": 600.033
  },
  {
    "name": "Sấm rền",
    "key": "audio/rolling-thunder-real.mp3",
    "group": "rain",
    "aliases": "Rolling Thunder",
    "source": "/sounds/rolling-thunder/",
    "duration": 600.033
  },
  {
    "name": "Mưa trên mặt hồ",
    "key": "audio/rain-lake-real.mp3",
    "group": "rain",
    "aliases": "Rain on Lake",
    "source": "/sounds/rain-on-lake/",
    "duration": 600.033
  },
  {
    "name": "Sông chảy xiết",
    "key": "audio/rushing-river-real.mp3",
    "group": "water",
    "aliases": "Rushing River",
    "source": "/sounds/rushing-river/",
    "duration": 600.033
  },
  {
    "name": "Suối rừng êm",
    "key": "audio/forest-stream-real.mp3",
    "group": "water",
    "aliases": "Gentle Forest Stream",
    "source": "/sounds/forest-stream/",
    "duration": 600.033
  },
  {
    "name": "Sóng biển nhẹ",
    "key": "audio/gentle-ocean-real.mp3",
    "group": "water",
    "aliases": "Gentle Ocean Waves",
    "source": "/sounds/gentle-ocean-waves/",
    "duration": 600.033
  },
  {
    "name": "Suối Bodetal và tiếng chim",
    "key": "audio/bodetal-brook-real.mp3",
    "group": "water",
    "aliases": "Bodetal Brook & Birds",
    "source": "/sounds/bodetal-brook-birds/",
    "duration": 600.033
  },
  {
    "name": "Sóng vỗ mạnh",
    "key": "audio/crashing-ocean-real.mp3",
    "group": "water",
    "aliases": "Crashing Ocean Waves",
    "source": "/sounds/crashing-ocean-waves/",
    "duration": 600.033
  },
  {
    "name": "Quạt tháp",
    "key": "audio/c6c-tower-fan-synth.mp3",
    "group": "fan",
    "aliases": "Tower Fan — Synthetic",
    "license": "WhiteNoiseChoir · Tổng hợp",
    "duration": 600.033
  },
  {
    "name": "Quạt xoay",
    "key": "audio/c6c-oscillating-fan-synth.mp3",
    "group": "fan",
    "aliases": "Oscillating Fan — Synthetic",
    "license": "WhiteNoiseChoir · Tổng hợp",
    "duration": 600.033
  },
  {
    "name": "Âm trong bụng mẹ",
    "key": "audio/c6c-womb-like-synth.mp3",
    "group": "human",
    "aliases": "Womb-like Sound — Synthetic",
    "license": "WhiteNoiseChoir · Tổng hợp",
    "duration": 600.033
  },
  {
    "name": "Tiếng suỵt nhẹ",
    "key": "audio/c6c-gentle-shushing-synth.mp3",
    "group": "human",
    "aliases": "Gentle Shushing — Synthetic",
    "license": "WhiteNoiseChoir · Tổng hợp",
    "duration": 600.033
  },
  {
    "name": "Nhịp tim nhẹ",
    "key": "audio/c6c-soft-heartbeat-synth.mp3",
    "group": "human",
    "aliases": "Soft Heartbeat — Synthetic",
    "license": "WhiteNoiseChoir · Tổng hợp",
    "duration": 600.033
  },
  {
    "name": "Hơi thở nhẹ",
    "key": "audio/c6c-gentle-breathing-synth.mp3",
    "group": "human",
    "aliases": "Gentle Breathing — Synthetic",
    "license": "WhiteNoiseChoir · Tổng hợp",
    "duration": 600.033
  },
  {
    "name": "Tiếng ồn xám",
    "key": "audio/c6c-grey-noise-synth.mp3",
    "group": "noise",
    "aliases": "Grey Noise — Experimental Synthetic",
    "license": "WhiteNoiseChoir · Tổng hợp",
    "duration": 600.033
  },
  {
    "name": "Nhiễu radio",
    "key": "audio/c6c-radio-static-synth.mp3",
    "group": "noise",
    "aliases": "Radio Static — Synthetic",
    "license": "WhiteNoiseChoir · Tổng hợp",
    "duration": 600.033
  },
  {
    "name": "Tiếng lách tách đĩa vinyl",
    "key": "audio/c6c-vinyl-crackle-synth.mp3",
    "group": "fire",
    "aliases": "Vinyl Crackle — Synthetic",
    "license": "WhiteNoiseChoir · Tổng hợp",
    "duration": 600.033
  },
  {
    "name": "Tiếng ù điện",
    "key": "audio/c6c-electrical-hum-synth.mp3",
    "group": "hum",
    "aliases": "Electrical Hum — Synthetic",
    "license": "WhiteNoiseChoir · Tổng hợp",
    "duration": 600.033
  },
  {
    "name": "Chó ngủ · hơi thở thật (nghe thử, CC BY 4.0)",
    "url": "https://cdn.freesound.org/previews/642/642326_3655844-lq.mp3",
    "group": "wildlife",
    "aliases": "Dog Sleeping Breathing iainmccurdy Luna dog sleep breathe 51 seconds external audio preview",
    "duration": 51.293,
    "source": "https://freesound.org/people/iainmccurdy/sounds/642326/",
    "license": "CC BY 4.0 · preview MP3",
    "credit": "Tác giả: iainmccurdy (Freesound) · Foley artist: Luna. Cần ghi công khi xuất bản. Đây là preview bitrate thấp; để làm master nên tải WAV gốc sau khi đăng nhập Freesound."
  },
  {
    "name": "Chó ngủ · tiếng thở/ngáy thật (CC0)",
    "url": "https://cdn.freesound.org/previews/482/482998_6150892-lq.mp3",
    "group": "wildlife",
    "aliases": "Sleeping Dog 1 SpaceJoe snoring dog breathing 3min external audio preview",
    "duration": 191.618,
    "source": "https://freesound.org/people/SpaceJoe/sounds/482998/",
    "license": "CC0 · preview MP3",
    "credit": "Tác giả: SpaceJoe (Freesound). Giấy phép CC0. Đây là preview bitrate thấp; để làm master nên tải WAV gốc sau khi đăng nhập Freesound."
  },
  {
    "name": "Dế đêm dịu · rừng gần suối · thử nguồn ngoài",
    "url": "https://cdn.freesound.org/previews/857/857163_12970089-lq.mp3",
    "group": "wildlife",
    "aliases": "quiet night soft crickets forest insects natural background Goldenboy76 external preview",
    "duration": 535.769,
    "source": "https://freesound.org/people/Goldenboy76/sounds/857163/",
    "license": "CC0 · MP3 preview",
    "credit": "Goldenboy76 · Quiet Night Atmosphere — Soft Crickets · Freesound (2026). Original WAV 48kHz mono. Bản Studio hiện dùng MP3 preview để nghe thử; khi xuất bản chính thức nên sử dụng WAV gốc."
  },
  {
    "name": "Dế kêu đêm · bản ghi sạch dự phòng",
    "url": "https://cdn.freesound.org/previews/522/522298_9084007-lq.mp3",
    "group": "wildlife",
    "aliases": "crickets at night clean sound Defelozedd94 insects forest outdoors alternative CC0",
    "duration": 169.002,
    "source": "https://freesound.org/people/Defelozedd94/sounds/522298/",
    "license": "CC0 · MP3 preview",
    "credit": "Defelozedd94 · Crickets At Night — Clean sound · Freesound (2020). Bản gốc WAV 48 kHz stereo. MP3 preview có thể nén thấp hơn."
  }
];
