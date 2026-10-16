<script lang="ts">
  import FaceEditor from '$lib/components/asset-viewer/face-editor/FaceEditor.svelte';
  import VideoRemoteViewer from '$lib/components/asset-viewer/VideoRemoteViewer.svelte';
  import { assetViewerFadeDuration } from '$lib/constants';
  import { assetViewerManager } from '$lib/managers/asset-viewer-manager.svelte';
  import { authManager } from '$lib/managers/auth-manager.svelte';
  import { castManager } from '$lib/managers/cast-manager.svelte';
  import { featureFlagsManager } from '$lib/managers/feature-flags-manager.svelte';
  import { mediaCapabilitiesManager } from '$lib/managers/media-capabilities-manager.svelte';
  import {
    autoPlayVideo,
    loopVideo as loopVideoPreference,
    videoViewerMuted,
    videoViewerVolume,
  } from '$lib/stores/preferences.store';
  import { getAssetHlsSessionUrl, getAssetHlsUrl, getAssetMediaUrl, getAssetPlaybackUrl } from '$lib/utils';
  import { AssetMediaSize, type AssetResponseDto } from '@immich/sdk';
  import { LoadingSpinner, shortcuts } from '@immich/ui';
  import 'hls-video-element';
  import type HlsVideoElement from 'hls-video-element';
  import Hls, { AbrController, Events, type FragLoadedData, type FragLoadingData, type HlsConfig } from 'hls.js';
  import { onDestroy, onMount } from 'svelte';
  import { useSwipe, type SwipeCustomEvent } from 'svelte-gestures';
  import { fade } from 'svelte/transition';
  import type { QualityOption, VideoFitMode, VideoStats } from './video-player/types';
  import VideoControlsBar from './video-player/VideoControlsBar.svelte';
  import VideoFeedbackOverlay from './video-player/VideoFeedbackOverlay.svelte';
  import VideoStatsForNerds from './video-player/VideoStatsForNerds.svelte';

  interface Props {
    asset: AssetResponseDto;
    assetId: string;
    loopVideo: boolean;
    cacheKey: string | null;
    playOriginalVideo: boolean;
    extendedControls?: boolean;
    onPreviousAsset?: () => void;
    onNextAsset?: () => void;
    onVideoEnded?: () => void;
    onVideoStarted?: () => void;
    onClose?: () => void;
  }

  let {
    asset,
    assetId,
    loopVideo,
    cacheKey,
    playOriginalVideo,
    extendedControls = false,
    onPreviousAsset = () => {},
    onNextAsset = () => {},
    onVideoEnded = () => {},
    onVideoStarted = () => {},
    onClose = () => {},
  }: Props = $props();

  const parseAssetDuration = (value: string | number | null | undefined): number => {
    if (!value) {
      return 0;
    }
    if (typeof value === 'number') {
      return Number.isFinite(value) ? value : 0;
    }
    const parts = value.split(':').map(Number);
    if (parts.length === 3 && parts.every(Number.isFinite)) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    const num = Number(value);
    return Number.isFinite(num) ? num : 0;
  };

  let containerElement: HTMLDivElement | undefined = $state();
  let videoPlayer: HTMLVideoElement | undefined = $state();
  let isLoading = $state(true);
  let hasLoadedMetadata = $state(false);
  let isPaused = $state(true);
  let currentTime = $state(0);
  let duration = $state(parseAssetDuration(asset.duration));
  let buffered: TimeRanges | null = $state(null);
  let playbackRate = $state(1);
  let previousRateBeforeBoost = $state(1);
  let isSpeedBoostActive = $state(false);
  let fitMode: VideoFitMode = $state('contain');
  let isAutoplayNext = $state(false);
  let isFullscreen = $state(false);
  let isSettingsOpen = $state(false);
  let showStatsForNerds = $state(false);
  let isScrubbing = $state(false);
  let showControls = $state(true);
  let hideControlsTimer: ReturnType<typeof setTimeout> | undefined;

  // Visual feedback states
  let showPlayFlash = $state(false);
  let playFlashTimer: ReturnType<typeof setTimeout> | undefined;
  let seekFeedback: { direction: 'left' | 'right'; seconds: number } | null = $state(null);
  let seekFeedbackTimer: ReturnType<typeof setTimeout> | undefined;
  let volumeFeedback: { volume: number; muted: boolean } | null = $state(null);
  let volumeFeedbackTimer: ReturnType<typeof setTimeout> | undefined;

  // Single vs double click disambiguation
  let clickTimer: ReturnType<typeof setTimeout> | undefined;
  let speedHoldTimer: ReturnType<typeof setTimeout> | undefined;

  // Stream & Quality management
  let isLiveTranscoding = $state(featureFlagsManager.value.realtimeTranscoding);
  let selectedQualityMode: 'auto' | 'original' | 'transcoded' | number = $state('auto');
  let availableQualities: QualityOption[] = $state([]);
  let currentResolutionLabel = $state('');
  let videoWidth = $state(0);
  let videoHeight = $state(0);
  let droppedFramesCount = $state(0);
  let totalFramesCount = $state(0);

  let showVideo = $state(false);
  let hasFocused = $state(false);
  let activeSession: { assetId: string; id: string } | undefined;
  let rebuildCount = 0;
  let statsUpdateTimer: ReturnType<typeof setInterval> | undefined;

  const MAX_REBUILDS = 1;
  const SESSION_ID_REGEX = /\/video\/stream\/([0-9a-f-]{36})\//;

  let containerWidth = $state(0);
  let containerHeight = $state(0);

  let useHls = $derived(
    isLiveTranscoding &&
      featureFlagsManager.value.realtimeTranscoding &&
      !playOriginalVideo &&
      selectedQualityMode !== 'original' &&
      selectedQualityMode !== 'transcoded',
  );

  // Derived URL based on active quality mode and live transcoding
  let assetFileUrl = $derived.by(() => {
    if (selectedQualityMode === 'original' || playOriginalVideo) {
      return getAssetMediaUrl({ id: assetId, size: AssetMediaSize.Original, cacheKey });
    }
    if (selectedQualityMode === 'transcoded') {
      return getAssetPlaybackUrl({ id: assetId, cacheKey });
    }
    if (useHls) {
      return getAssetHlsUrl(assetId);
    }
    return getAssetPlaybackUrl({ id: assetId, cacheKey });
  });

  const activeQualityId = $derived.by(() => {
    if (typeof selectedQualityMode === 'number') {
      return `hls-${selectedQualityMode}`;
    }
    return selectedQualityMode;
  });

  class NoAbandonAbrController extends AbrController {
    private switchTarget = -1;

    protected override onFragLoading(_event: Events.FRAG_LOADING, data: FragLoadingData) {
      if (data.frag.sn === 'initSegment') {
        this.switchTarget = data.frag.level;
      }
    }

    protected override onFragLoaded(event: Events.FRAG_LOADED, data: FragLoadedData) {
      if (data.frag.sn !== 'initSegment') {
        this.switchTarget = -1;
      }
      super.onFragLoaded(event, data);
    }

    override get nextAutoLevel(): number {
      const level = super.nextAutoLevel;
      const target = this.hls.levels[this.switchTarget];
      if (target && level < this.switchTarget && target.loadError === 0 && target.fragmentError === 0) {
        return this.switchTarget;
      }
      return level;
    }

    override set nextAutoLevel(level: number) {
      super.nextAutoLevel = level;
    }
  }

  const hlsConfig: Partial<HlsConfig> = {
    abrController: NoAbandonAbrController,
    highBufferWatchdogPeriod: 10,
    detectStallWithCurrentTimeMs: 10_000,
    maxBufferHole: 0.5,
    maxBufferLength: 30,
    maxMaxBufferLength: 60,
    fragLoadPolicy: {
      default: {
        maxTimeToFirstByteMs: 30_000,
        maxLoadTimeMs: 60_000,
        timeoutRetry: { maxNumRetry: 5, retryDelayMs: 100, maxRetryDelayMs: 0 },
        errorRetry: { maxNumRetry: 3, retryDelayMs: 1000, maxRetryDelayMs: 8000 },
      },
    },
    useMediaCapabilities: false,
    xhrSetup: (xhr: XMLHttpRequest, url: string) => {
      const authenticatedUrl = new URL(url, location.origin);
      for (const [key, value] of Object.entries(authManager.params)) {
        if (value) {
          authenticatedUrl.searchParams.set(key, value as string);
        }
      }
      xhr.open('GET', authenticatedUrl.href);
    },
  };

  const releaseSession = () => {
    const session = activeSession;
    if (!session) {
      return;
    }
    activeSession = undefined;
    const url = getAssetHlsSessionUrl(session.assetId, session.id);
    void fetch(url, { method: 'DELETE' }).catch(() => console.warn('Failed to release HLS session', session));
  };

  const isHlsElement = (el: HTMLVideoElement | undefined): el is HlsVideoElement => {
    return el?.tagName === 'HLS-VIDEO';
  };

  const updateQualitiesList = (hlsApi?: Hls) => {
    const list: QualityOption[] = [];

    // Auto option
    list.push({
      id: 'auto',
      label: currentResolutionLabel ? `Auto (${currentResolutionLabel})` : 'Auto (Recommended)',
      resolutionLabel: currentResolutionLabel || undefined,
    });

    // If HLS levels exist, add individual resolutions
    if (hlsApi && hlsApi.levels && hlsApi.levels.length > 0) {
      for (const [index, level] of hlsApi.levels.entries()) {
        const height = level.height;
        const resName =
          height >= 2160 ? '4K 2160p' : height >= 1440 ? '2K 1440p' : height >= 720 ? `${height}p HD` : `${height}p`;
        list.push({
          id: `hls-${index}`,
          label: resName,
          resolutionLabel: height >= 720 ? 'HD' : undefined,
          height: level.height,
          width: level.width,
          bitrate: level.bitrate,
          codec: level.videoCodec,
          isHls: true,
          levelIndex: index,
        });
      }
    }

    // Direct stream options
    const origHeight = asset.height || 1080;
    const origLabel =
      origHeight >= 2160 ? 'Original (4K)' : origHeight >= 1080 ? 'Original (1080p)' : 'Original (Source)';
    list.push(
      {
        id: 'original',
        label: origLabel,
        resolutionLabel: 'SOURCE',
        height: asset.height || undefined,
        width: asset.width || undefined,
      },
      {
        id: 'transcoded',
        label: 'Optimized (Web MP4)',
        resolutionLabel: 'MP4',
      },
    );

    availableQualities = list;
  };

  const wireHlsListeners = (el: HlsVideoElement, currentAssetId: string, resumeTime?: number) => {
    const api = el.api;
    if (!api) {
      return;
    }

    Object.defineProperty(api, 'nextLevel', {
      configurable: true,
      get: () => api.currentLevel,
      set: (level: number) => {
        api.currentLevel = level;
      },
    });

    // eslint-disable-next-line @typescript-eslint/no-misused-promises
    api.on(Hls.Events.MANIFEST_PARSED, async () => {
      api.stopLoad();
      const id = api.levels[0]?.url[0]?.match(SESSION_ID_REGEX)?.[1];
      if (id) {
        activeSession = { assetId: currentAssetId, id };
      }

      const keep = await mediaCapabilitiesManager.efficientLevels(api.levels);
      for (let i = api.levels.length - 1; i >= 0; i--) {
        if (!keep.has(i)) {
          api.removeLevel(i);
        }
      }

      updateQualitiesList(api);

      // If user selected a specific HLS level previously
      if (typeof selectedQualityMode === 'number') {
        api.currentLevel = selectedQualityMode;
      } else {
        api.currentLevel = -1; // Auto
      }

      api.startLoad(resumeTime);
    });

    api.on(Hls.Events.LEVEL_SWITCHED, (_, data) => {
      const level = api.levels[data.level];
      if (level) {
        currentResolutionLabel = `${level.height}p`;
        updateQualitiesList(api);
      }
    });

    api.on(Hls.Events.FRAG_LOADED, () => (rebuildCount = 0));

    api.on(Hls.Events.ERROR, (_, data) => {
      if (
        !data.fatal ||
        data.details !== Hls.ErrorDetails.FRAG_LOAD_ERROR ||
        data.response?.code !== 404 ||
        rebuildCount++ >= MAX_REBUILDS
      ) {
        // Fallback gracefully to direct playback if HLS fails completely
        if (data.fatal && isLiveTranscoding) {
          console.warn('HLS stream fatal error, falling back to direct video stream');
          isLiveTranscoding = false;
          selectedQualityMode = 'transcoded';
        }
        return;
      }
      console.warn('Error loading segment, restarting session');
      activeSession = undefined;
      resumeTime = el.currentTime;
      el.load();
      queueMicrotask(() => wireHlsListeners(el, currentAssetId, resumeTime));
    });
  };

  onMount(() => {
    showVideo = true;
    updateQualitiesList();

    // Stats periodic refresher
    statsUpdateTimer = setInterval(() => {
      if (videoPlayer) {
        currentTime = videoPlayer.currentTime;
        duration = videoPlayer.duration || parseAssetDuration(asset.duration);
        buffered = videoPlayer.buffered;
        videoWidth = videoPlayer.videoWidth;
        videoHeight = videoPlayer.videoHeight;

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const quality = (videoPlayer as any).getVideoPlaybackQuality?.();
        if (quality) {
          droppedFramesCount = quality.droppedVideoFrames;
          totalFramesCount = quality.totalVideoFrames;
        }
      }
    }, 500);
  });

  onDestroy(() => {
    if (statsUpdateTimer) {
      clearInterval(statsUpdateTimer);
    }
    if (hideControlsTimer) {
      clearTimeout(hideControlsTimer);
    }
    if (playFlashTimer) {
      clearTimeout(playFlashTimer);
    }
    if (clickTimer) {
      clearTimeout(clickTimer);
    }
    if (speedHoldTimer) {
      clearTimeout(speedHoldTimer);
    }
    if (seekFeedbackTimer) {
      clearTimeout(seekFeedbackTimer);
    }
    if (volumeFeedbackTimer) {
      clearTimeout(volumeFeedbackTimer);
    }
    releaseSession();
    if (videoPlayer) {
      videoPlayer.src = '';
    }
  });

  $effect(() => {
    // When URL or source changes
    if (videoPlayer && assetFileUrl) {
      hasFocused = false;
      hasLoadedMetadata = false;
      rebuildCount = 0;
      releaseSession();
      if (isHlsElement(videoPlayer)) {
        videoPlayer.config = hlsConfig;
        videoPlayer.src = assetFileUrl;
        const el = videoPlayer;
        queueMicrotask(() => wireHlsListeners(el, assetId));
      } else {
        videoPlayer.load();
      }
    }
    return releaseSession;
  });

  const onPagehide = (event: PageTransitionEvent) => {
    if (!event.persisted) {
      releaseSession();
    }
  };

  const onFullscreenChange = () => {
    isFullscreen = Boolean(document.fullscreenElement);
  };

  $effect(() => {
    window.addEventListener('pagehide', onPagehide);
    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => {
      window.removeEventListener('pagehide', onPagehide);
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    };
  });

  const resetHideControlsTimer = () => {
    showControls = true;
    if (hideControlsTimer) {
      clearTimeout(hideControlsTimer);
    }
    if (!isPaused && !isSettingsOpen && !isScrubbing) {
      hideControlsTimer = setTimeout(() => {
        showControls = false;
      }, 2500);
    }
  };

  const handleCanPlay = async (video: HTMLVideoElement) => {
    try {
      video.volume = $videoViewerVolume;
      video.muted = $videoViewerMuted;
      video.playbackRate = playbackRate;
      if (!video.paused) {
        await video.play();
        onVideoStarted();
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'NotAllowedError') {
        try {
          video.muted = true;
          $videoViewerMuted = true;
          await video.play();
          onVideoStarted();
        } catch {
          // ignore auto-play failure
        }
      }
    } finally {
      isLoading = false;
    }
  };

  // Playback Controls
  const togglePlay = () => {
    if (!videoPlayer) {
      return;
    }
    if (videoPlayer.paused) {
      void videoPlayer.play();
      isPaused = false;
      flashPlayIcon(false);
    } else {
      videoPlayer.pause();
      isPaused = true;
      flashPlayIcon(true);
    }
    resetHideControlsTimer();
  };

  const flashPlayIcon = (paused: boolean) => {
    showPlayFlash = true;
    isPaused = paused;
    if (playFlashTimer) {
      clearTimeout(playFlashTimer);
    }
    playFlashTimer = setTimeout(() => {
      showPlayFlash = false;
    }, 400);
  };

  const seekRelative = (seconds: number) => {
    if (!videoPlayer) {
      return;
    }
    const newTime = Math.max(0, Math.min(videoPlayer.duration || duration, videoPlayer.currentTime + seconds));
    videoPlayer.currentTime = newTime;
    currentTime = newTime;

    // Show seek feedback badge
    const direction = seconds < 0 ? 'left' : 'right';
    const currentFeedbackSeconds =
      seekFeedback?.direction === direction ? seekFeedback.seconds + Math.abs(seconds) : Math.abs(seconds);
    seekFeedback = { direction, seconds: currentFeedbackSeconds };

    if (seekFeedbackTimer) {
      clearTimeout(seekFeedbackTimer);
    }
    seekFeedbackTimer = setTimeout(() => {
      seekFeedback = null;
    }, 700);

    resetHideControlsTimer();
  };

  const handleSeek = (time: number) => {
    if (!videoPlayer) {
      return;
    }
    videoPlayer.currentTime = time;
    currentTime = time;
    resetHideControlsTimer();
  };

  const adjustVolume = (delta: number) => {
    if (!videoPlayer) {
      return;
    }
    const newVol = Math.max(0, Math.min(1, Math.round((videoPlayer.volume + delta) * 20) / 20));
    videoPlayer.volume = newVol;
    $videoViewerVolume = newVol;
    if (newVol > 0 && videoPlayer.muted) {
      videoPlayer.muted = false;
      $videoViewerMuted = false;
    }

    volumeFeedback = { volume: newVol, muted: videoPlayer.muted };
    if (volumeFeedbackTimer) {
      clearTimeout(volumeFeedbackTimer);
    }
    volumeFeedbackTimer = setTimeout(() => {
      volumeFeedback = null;
    }, 1200);

    resetHideControlsTimer();
  };

  const handleVolumeChange = (newVol: number) => {
    if (!videoPlayer) {
      return;
    }
    videoPlayer.volume = newVol;
    $videoViewerVolume = newVol;
    if (newVol > 0 && videoPlayer.muted) {
      videoPlayer.muted = false;
      $videoViewerMuted = false;
    }
    resetHideControlsTimer();
  };

  const toggleMute = () => {
    if (!videoPlayer) {
      return;
    }
    videoPlayer.muted = !videoPlayer.muted;
    $videoViewerMuted = videoPlayer.muted;

    volumeFeedback = { volume: videoPlayer.volume, muted: videoPlayer.muted };
    if (volumeFeedbackTimer) {
      clearTimeout(volumeFeedbackTimer);
    }
    volumeFeedbackTimer = setTimeout(() => {
      volumeFeedback = null;
    }, 1200);

    resetHideControlsTimer();
  };

  const handleSelectSpeed = (speed: number) => {
    playbackRate = speed;
    if (videoPlayer) {
      videoPlayer.playbackRate = speed;
    }
    resetHideControlsTimer();
  };

  const handleSelectQuality = (quality: QualityOption) => {
    if (!videoPlayer) {
      return;
    }
    const curTime = videoPlayer.currentTime;
    const wasPlaying = !videoPlayer.paused;

    switch (quality.id) {
      case 'original': {
        selectedQualityMode = 'original';
        isLiveTranscoding = false;

        break;
      }
      case 'transcoded': {
        selectedQualityMode = 'transcoded';
        isLiveTranscoding = false;

        break;
      }
      case 'auto': {
        selectedQualityMode = 'auto';
        isLiveTranscoding = true;
        if (isHlsElement(videoPlayer) && videoPlayer.api) {
          videoPlayer.api.currentLevel = -1;
        }

        break;
      }
      default: {
        if (quality.isHls && quality.levelIndex !== undefined) {
          selectedQualityMode = quality.levelIndex;
          isLiveTranscoding = true;
          if (isHlsElement(videoPlayer) && videoPlayer.api) {
            videoPlayer.api.currentLevel = quality.levelIndex;
          }
        }
      }
    }

    queueMicrotask(() => {
      if (videoPlayer) {
        videoPlayer.currentTime = curTime;
        if (wasPlaying) {
          void videoPlayer.play();
        }
      }
    });

    resetHideControlsTimer();
  };

  const toggleFullscreen = async () => {
    if (!containerElement) {
      return;
    }
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
        isFullscreen = false;
      } else {
        await containerElement.requestFullscreen();
        isFullscreen = true;
      }
    } catch {
      // Fullscreen not permitted or failed
    }
    resetHideControlsTimer();
  };

  const togglePiP = async () => {
    if (!videoPlayer) {
      return;
    }
    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
      } else if (document.pictureInPictureEnabled) {
        await videoPlayer.requestPictureInPicture();
      }
    } catch {
      // PiP not available or failed
    }
    resetHideControlsTimer();
  };

  const toggleFitMode = () => {
    fitMode = fitMode === 'contain' ? 'cover' : 'contain';
    resetHideControlsTimer();
  };

  const toggleLiveTranscoding = () => {
    isLiveTranscoding = !isLiveTranscoding;
    selectedQualityMode = isLiveTranscoding ? 'auto' : 'transcoded';
    resetHideControlsTimer();
  };

  // Video Container Interactions (Single click vs double click vs hold to 2x speed)
  const handleVideoPointerDown = (event: PointerEvent) => {
    // Only primary button
    if (event.button !== 0) {
      return;
    }

    // Hold for 2x speed (long press YouTube gesture)
    speedHoldTimer = setTimeout(() => {
      if (videoPlayer && !videoPlayer.paused) {
        previousRateBeforeBoost = videoPlayer.playbackRate;
        videoPlayer.playbackRate = 2;
        isSpeedBoostActive = true;
      }
    }, 400);
  };

  const handleVideoPointerUp = () => {
    if (speedHoldTimer) {
      clearTimeout(speedHoldTimer);
      speedHoldTimer = undefined;
    }
    if (isSpeedBoostActive) {
      isSpeedBoostActive = false;
      if (videoPlayer) {
        videoPlayer.playbackRate = previousRateBeforeBoost;
      }
    }
  };

  const handleVideoAreaClick = (event: MouseEvent) => {
    if (isSpeedBoostActive) {
      return;
    }

    const rect = containerElement?.getBoundingClientRect();
    if (!rect) {
      return;
    }
    const relativeX = (event.clientX - rect.left) / rect.width;

    if (clickTimer) {
      // Double click detected!
      clearTimeout(clickTimer);
      clickTimer = undefined;

      if (relativeX < 0.35) {
        // Double click left: rewind 10s
        seekRelative(-10);
      } else if (relativeX > 0.65) {
        // Double click right: forward 10s
        seekRelative(10);
      } else {
        // Double click center: fullscreen
        void toggleFullscreen();
      }
    } else {
      // Wait to see if second click arrives
      clickTimer = setTimeout(() => {
        clickTimer = undefined;
        // Single click: toggle play/pause
        togglePlay();
      }, 250);
    }
  };

  const handleVideoEnded = () => {
    if ($loopVideoPreference && loopVideo) {
      if (videoPlayer) {
        videoPlayer.currentTime = 0;
        void videoPlayer.play();
      }
      return;
    }
    onVideoEnded();
    if (isAutoplayNext) {
      onNextAsset();
    }
  };

  const onSwipe = (event: SwipeCustomEvent) => {
    if (event.detail.direction === 'left') {
      onNextAsset();
    } else if (event.detail.direction === 'right') {
      onPreviousAsset();
    }
  };

  const statsData: VideoStats = $derived.by(() => {
    const buf = buffered;
    let bufferHealthStr = '0s';
    if (buf && buf.length > 0) {
      const end = buf.end(buf.length - 1);
      bufferHealthStr = `${Math.max(0, end - currentTime).toFixed(1)}s`;
    }
    return {
      assetId: asset.id.slice(0, 13) + '...',
      viewport: `${containerWidth}x${containerHeight}`,
      currentResolution: `${videoWidth}x${videoHeight}`,
      optimalResolution: asset.width && asset.height ? `${asset.width}x${asset.height}` : 'Auto',
      droppedFrames: totalFramesCount > 0 ? `${droppedFramesCount} / ${totalFramesCount}` : '0',
      streamType: useHls ? 'HLS Live Transcode' : 'Direct MP4 Stream',
      codecs:
        isHlsElement(videoPlayer) && videoPlayer.api?.levels?.[0]?.videoCodec
          ? videoPlayer.api.levels[0].videoCodec
          : 'mp4 / avc1',
      currentTime: `${currentTime.toFixed(1)}s`,
      duration: `${duration.toFixed(1)}s`,
      bufferHealth: bufferHealthStr,
      volume: `${Math.round($videoViewerVolume * 100)}% (${$videoViewerMuted ? 'muted' : 'unmuted'})`,
      playbackRate: `${playbackRate}x`,
    };
  });

  $effect(() => {
    if (assetViewerManager.isFaceEditMode) {
      videoPlayer?.pause();
      isPaused = true;
    }
  });
</script>

<svelte:body
  use:shortcuts={[
    {
      shortcut: { key: ' ' },
      onShortcut: togglePlay,
    },
    {
      shortcut: { key: 'k' },
      onShortcut: togglePlay,
    },
    {
      shortcut: { key: 'j' },
      onShortcut: () => seekRelative(-10),
    },
    {
      shortcut: { key: 'ArrowLeft', shift: true },
      onShortcut: () => seekRelative(-5),
    },
    {
      shortcut: { key: 'ArrowRight', shift: true },
      onShortcut: () => seekRelative(5),
    },
    {
      shortcut: { key: 'ArrowUp', shift: true },
      onShortcut: () => adjustVolume(0.05),
    },
    {
      shortcut: { key: 'ArrowDown', shift: true },
      onShortcut: () => adjustVolume(-0.05),
    },
    {
      shortcut: { key: 'm' },
      onShortcut: toggleMute,
    },
    {
      shortcut: { key: 'F', shift: true },
      onShortcut: toggleFullscreen,
    },
    {
      shortcut: { key: '[' },
      onShortcut: () => seekRelative(-1 / 30),
    },
    {
      shortcut: { key: ']' },
      onShortcut: () => seekRelative(1 / 30),
    },
    {
      shortcut: { key: '<' },
      onShortcut: () => handleSelectSpeed(Math.max(0.25, playbackRate - 0.25)),
    },
    {
      shortcut: { key: '>' },
      onShortcut: () => handleSelectSpeed(Math.min(3, playbackRate + 0.25)),
    },
  ]}
/>

{#if showVideo}
  <div
    bind:this={containerElement}
    role="region"
    aria-label="Video player"
    transition:fade={{ duration: assetViewerFadeDuration }}
    class="relative flex size-full place-content-center place-items-center overflow-hidden bg-black select-none {showControls
      ? 'cursor-default'
      : 'cursor-none'}"
    bind:clientWidth={containerWidth}
    bind:clientHeight={containerHeight}
    onmousemove={resetHideControlsTimer}
    onmouseenter={resetHideControlsTimer}
  >
    {#if castManager.isCasting}
      <div class="h-full place-content-center place-items-center">
        <VideoRemoteViewer
          poster={getAssetMediaUrl({ id: assetId, size: AssetMediaSize.Preview, cacheKey })}
          {onVideoStarted}
          {onVideoEnded}
          {assetFileUrl}
        />
      </div>
    {:else}
      <!-- Video Element Area with Gestures -->
      <div
        role="presentation"
        class="relative flex size-full items-center justify-center overflow-hidden"
        onclick={handleVideoAreaClick}
        onpointerdown={handleVideoPointerDown}
        onpointerup={handleVideoPointerUp}
        onpointercancel={handleVideoPointerUp}
      >
        {#if useHls}
          <hls-video
            bind:this={videoPlayer}
            loop={$loopVideoPreference && loopVideo}
            autoplay={$autoPlayVideo}
            disablePictureInPicture={!extendedControls}
            playsinline
            {...useSwipe(onSwipe)}
            class="size-full {fitMode === 'cover' ? 'object-cover' : 'object-contain'}"
            onloadedmetadata={() => (hasLoadedMetadata = true)}
            oncanplay={(e: Event) => handleCanPlay(e.currentTarget as HTMLVideoElement)}
            onplay={() => (isPaused = false)}
            onpause={() => (isPaused = true)}
            ontimeupdate={() => {
              if (videoPlayer && !isScrubbing) {
                currentTime = videoPlayer.currentTime;
                buffered = videoPlayer.buffered;
              }
            }}
            onended={handleVideoEnded}
            onplaying={(e: Event) => {
              if (hasFocused) {
                return;
              }
              (e.currentTarget as HTMLElement).focus();
              hasFocused = true;
            }}
            onclose={onClose}
            poster={getAssetMediaUrl({ id: asset.id, size: AssetMediaSize.Preview, cacheKey })}
          ></hls-video>
        {:else}
          <video
            bind:this={videoPlayer}
            src={assetFileUrl}
            loop={$loopVideoPreference && loopVideo}
            autoplay={$autoPlayVideo}
            disablePictureInPicture={!extendedControls}
            playsinline
            {...useSwipe(onSwipe)}
            class="size-full {fitMode === 'cover' ? 'object-cover' : 'object-contain'}"
            onloadedmetadata={() => (hasLoadedMetadata = true)}
            oncanplay={(e) => handleCanPlay(e.currentTarget)}
            onplay={() => (isPaused = false)}
            onpause={() => (isPaused = true)}
            ontimeupdate={() => {
              if (videoPlayer && !isScrubbing) {
                currentTime = videoPlayer.currentTime;
                buffered = videoPlayer.buffered;
              }
            }}
            onended={handleVideoEnded}
            onplaying={(e) => {
              if (hasFocused) {
                return;
              }
              e.currentTarget.focus();
              hasFocused = true;
            }}
            onclose={onClose}
            poster={getAssetMediaUrl({ id: asset.id, size: AssetMediaSize.Preview, cacheKey })}
          ></video>
        {/if}

        <!-- Interactive YouTube Feedback Overlay (Center play flash, double-click ripples, 2x hold, volume toast) -->
        <VideoFeedbackOverlay {showPlayFlash} {isPaused} {seekFeedback} {isSpeedBoostActive} {volumeFeedback} />
      </div>

      <!-- Stats for Nerds Overlay -->
      {#if showStatsForNerds}
        <VideoStatsForNerds stats={statsData} onClose={() => (showStatsForNerds = false)} />
      {/if}

      <!-- YouTube Controls Bar (Bottom) -->
      {#if extendedControls}
        <div
          class="absolute inset-x-0 bottom-0 z-30 transition-opacity duration-300 {showControls ||
          isPaused ||
          isSettingsOpen ||
          isScrubbing
            ? 'opacity-100'
            : 'pointer-events-none opacity-0'}"
        >
          <VideoControlsBar
            {isPaused}
            {currentTime}
            {duration}
            {buffered}
            volume={$videoViewerVolume}
            isMuted={$videoViewerMuted}
            {playbackRate}
            {fitMode}
            {isAutoplayNext}
            {isFullscreen}
            {isSettingsOpen}
            qualities={availableQualities}
            {activeQualityId}
            isLooping={$loopVideoPreference && loopVideo}
            {isLiveTranscoding}
            canLiveTranscode={featureFlagsManager.value.realtimeTranscoding}
            {showStatsForNerds}
            hasPreviousAsset={Boolean(onPreviousAsset)}
            hasNextAsset={Boolean(onNextAsset)}
            onTogglePlay={togglePlay}
            {onPreviousAsset}
            {onNextAsset}
            onSeek={handleSeek}
            onScrubStateChange={(scrubbing) => {
              isScrubbing = scrubbing;
              resetHideControlsTimer();
            }}
            onVolumeChange={handleVolumeChange}
            onToggleMute={toggleMute}
            onToggleAutoplayNext={() => (isAutoplayNext = !isAutoplayNext)}
            onTogglePiP={togglePiP}
            onToggleFitMode={toggleFitMode}
            onToggleSettings={() => {
              isSettingsOpen = !isSettingsOpen;
              resetHideControlsTimer();
            }}
            onCloseSettings={() => {
              isSettingsOpen = false;
              resetHideControlsTimer();
            }}
            onToggleFullscreen={toggleFullscreen}
            onSelectSpeed={handleSelectSpeed}
            onSelectQuality={handleSelectQuality}
            onToggleLoop={() => ($loopVideoPreference = !$loopVideoPreference)}
            onToggleLiveTranscoding={toggleLiveTranscoding}
            onToggleStatsForNerds={() => (showStatsForNerds = !showStatsForNerds)}
          />
        </div>
      {/if}

      <!-- Loading Spinner -->
      {#if isLoading}
        <div class="pointer-events-none absolute flex place-content-center place-items-center">
          <LoadingSpinner />
        </div>
      {/if}

      <!-- Face Editor Overlay -->
      {#if assetViewerManager.isFaceEditMode && videoPlayer && hasLoadedMetadata}
        <FaceEditor htmlElement={videoPlayer} {containerWidth} {containerHeight} {assetId} />
      {/if}
    {/if}
  </div>
{/if}
