/* WhiteNoiseChoir Studio — optional audio/video preview. The audio engine remains authoritative.
 * Reuses the existing local video-input and video-preview; never uploads the clip.
 */
(function () {
  'use strict';
  const panel = document.getElementById('av-live-preview');
  const input = document.getElementById('video-input');
  const video = document.getElementById('video-preview');
  const slot = document.getElementById('av-video-slot');
  const details = document.getElementById('av-preview-details');
  const status = document.getElementById('av-preview-status');
  const placeholder = document.getElementById('av-preview-placeholder');
  const name = document.getElementById('av-preview-name');
  const clock = document.getElementById('av-preview-clock');
  const remove = document.getElementById('av-remove-video');
  if (!panel || !input || !video || !slot || !details || !status || !placeholder || !name || !clock || !remove) return;

  // Keep the existing render/mux pipeline and file input intact. Moving the DOM
  // video element preserves the old onchange handler and the same object URL.
  slot.appendChild(video);
  video.controls = false; // The audio timeline is the ONLY transport.
  video.muted = true;
  video.defaultMuted = true;
  video.volume = 0;
  video.loop = true;
  video.playsInline = true;
  video.setAttribute('playsinline', '');
  video.preload = 'metadata';
  video.disablePictureInPicture = true;
  video.setAttribute('aria-label', 'Video không âm thanh, đồng bộ với timeline phối âm');

  let lastFrameTime = 0;
  let lastAudioPosition = null;
  let lastHardSeek = -Infinity;
  let lastPlayAttempt = -Infinity;
  let playPending = false;
  let lastStatus = '';
  let userPausedPanel = false;

  function message(value) {
    if (lastStatus !== value) {
      lastStatus = value;
      status.textContent = value;
    }
  }

  function showSelectedFile() {
    const file = input.files && input.files[0];
    const attached = Boolean(file);
    name.textContent = attached ? file.name : 'Chưa có video';
    placeholder.hidden = attached;
    remove.disabled = !attached;
    if (attached) {
      details.open = true;
      userPausedPanel = false;
      message('Đã gắn clip từ máy. Nhấn Phát trên timeline để xem và nghe đồng bộ.');
    } else {
      video.pause();
      clock.textContent = '--:-- / --:--';
      message('Chọn clip MP4 từ máy để xem cùng bản phối. Không tải lên máy chủ.');
    }
    lastAudioPosition = null;
    lastHardSeek = -Infinity;
    lastPlayAttempt = -Infinity;
  }

  function audioState() {
    // Read-only integration with the existing engine. No audio functions,
    // mix parameters, render state or event handlers are overridden.
    return {
      time: Number.isFinite(position) ? position : Number(document.getElementById('seek').value || 0),
      active: Boolean(playing && !loading && !exporting)
    };
  }

  function phase(time, duration) {
    return ((time % duration) + duration) % duration;
  }

  function signedDrift(expected, actual, duration) {
    let difference = expected - actual;
    if (difference > duration / 2) difference -= duration;
    if (difference < -duration / 2) difference += duration;
    return difference;
  }

  function alignVideo(expected, now) {
    try {
      if (Math.abs(signedDrift(expected, video.currentTime, video.duration)) > 0.08) {
        video.currentTime = expected;
      }
      lastHardSeek = now;
    } catch (_) {
      // Seek may be refused until the first decoded frame. Retry when ready.
    }
  }

  function update(now) {
    requestAnimationFrame(update);
    if (!input.files || !input.files.length || video.error) return;
    const duration = video.duration;
    if (!Number.isFinite(duration) || duration <= 0) return;
    const state = audioState();
    const expected = phase(state.time, duration);
    const elapsed = lastFrameTime ? (now - lastFrameTime) / 1000 : 0;
    const jumped = lastAudioPosition !== null &&
      Math.abs(state.time - lastAudioPosition) > Math.max(0.45, elapsed + 0.35);
    lastAudioPosition = state.time;
    lastFrameTime = now;
    const active = state.active && !document.hidden && !userPausedPanel;
    let difference = signedDrift(expected, video.currentTime, duration);

    if (jumped) {
      alignVideo(expected, now);
      difference = 0;
    }
    if (active) {
      if (video.paused && !playPending && now - lastPlayAttempt > 1250) {
        lastPlayAttempt = now;
        playPending = true;
        const result = video.play(); // muted + playsinline permits non-gesture playback.
        if (result && typeof result.then === 'function') {
          result.then(() => { playPending = false; })
            .catch(() => {
              playPending = false;
              message('Trình duyệt chặn video. Nhấn Phát trên timeline thêm lần nữa.');
            });
        } else playPending = false;
      }
      if (Math.abs(difference) > 0.36 && now - lastHardSeek > 1100) {
        alignVideo(expected, now);
        difference = 0;
      }
      // Small corrections are smooth; do not constantly seek and visibly stutter.
      video.playbackRate = Math.max(0.97, Math.min(1.03, 1 + difference * 0.1));
    } else {
      if (!video.paused) video.pause();
      video.playbackRate = 1;
      if (Math.abs(difference) > 0.08 && now - lastHardSeek > 100) {
        alignVideo(expected, now);
      }
    }
    if (clock.textContent !== formatPhase(expected) + ' / ' + formatPhase(duration)) {
      clock.textContent = formatPhase(expected) + ' / ' + formatPhase(duration);
    }
    if (active && !video.paused && !video.seeking) {
      message('Đang phát đồng bộ · Video tắt âm gốc');
    } else if (!state.active) {
      message('Sẵn sàng · Phát/tua bằng timeline âm thanh');
    }
  }

  function formatPhase(seconds) {
    const full = Math.max(0, Math.floor(seconds));
    return String(Math.floor(full / 60)).padStart(2, '0') + ':' +
      String(full % 60).padStart(2, '0');
  }

  video.addEventListener('loadedmetadata', () => {
    if (!Number.isFinite(video.duration) || video.duration <= 0) {
      message('Không đọc được thời lượng video. Vui lòng dùng MP4 H.264.');
      return;
    }
    message('Clip ' + formatPhase(video.duration) + ' đã sẵn sàng · Nhấn Phát trên timeline.');
    alignVideo(phase(audioState().time, video.duration), performance.now());
  });
  video.addEventListener('error', () => {
    message('Trình duyệt không phát được clip này. Nên chọn MP4 H.264 (không âm thanh).');
  });
  input.addEventListener('change', showSelectedFile);
  remove.addEventListener('click', () => {
    if (!input.files.length) return;
    input.value = '';
    input.dispatchEvent(new Event('change', {bubbles: true}));
  });

  // Drag a clip into the preview. The existing pipeline still owns the file.
  panel.addEventListener('dragover', event => {
    if (event.dataTransfer && Array.from(event.dataTransfer.types).includes('Files')) {
      event.preventDefault();
      panel.classList.add('av-drop-active');
    }
  });
  panel.addEventListener('dragleave', event => {
    if (!panel.contains(event.relatedTarget)) panel.classList.remove('av-drop-active');
  });
  panel.addEventListener('drop', event => {
    panel.classList.remove('av-drop-active');
    const file = event.dataTransfer && event.dataTransfer.files[0];
    if (!file) return;
    event.preventDefault();
    if (!file.type.startsWith('video/') && !/\.(mp4|mov|mkv|webm)$/i.test(file.name)) {
      message('Chỉ nhận file video (khuyến nghị MP4 H.264).');
      return;
    }
    try {
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      input.dispatchEvent(new Event('change', {bubbles: true}));
    } catch (_) {
      message('Trình duyệt chưa hỗ trợ kéo thả. Hãy bấm Chọn clip từ máy.');
    }
  });

  // Unlike the audio engine, this preview never schedules, alters or renders sound.
  showSelectedFile();
  requestAnimationFrame(update);
})();
