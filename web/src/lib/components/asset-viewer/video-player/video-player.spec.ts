import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import VideoControlsBar from './VideoControlsBar.svelte';
import VideoFeedbackOverlay from './VideoFeedbackOverlay.svelte';
import VideoScrubber from './VideoScrubber.svelte';
import VideoSettingsMenu from './VideoSettingsMenu.svelte';
import VideoStatsForNerds from './VideoStatsForNerds.svelte';

describe('YouTube Video Player Components', () => {
  describe('VideoScrubber', () => {
    it('renders with correct aria attributes and progress', () => {
      const onSeek = vi.fn();
      const { getByRole } = render(VideoScrubber, {
        currentTime: 30,
        duration: 120,
        buffered: null,
        onSeek,
      });

      const slider = getByRole('slider');
      expect(slider).toBeInTheDocument();
      expect(slider.getAttribute('aria-valuemax')).toBe('120');
      expect(slider.getAttribute('aria-valuenow')).toBe('30');
    });

    it('triggers seek on pointer click', async () => {
      const onSeek = vi.fn();
      const { getByRole } = render(VideoScrubber, {
        currentTime: 0,
        duration: 100,
        buffered: null,
        onSeek,
      });

      const slider = getByRole('slider');
      await fireEvent.pointerDown(slider, { clientX: 50, pointerId: 1 });
      expect(onSeek).toHaveBeenCalled();
    });
  });

  describe('VideoSettingsMenu', () => {
    it('renders main menu items when open', () => {
      const qualities = [
        { id: 'auto', label: 'Auto (1080p)' },
        { id: '1080p', label: '1080p HD' },
        { id: '720p', label: '720p' },
      ];

      const { getByText } = render(VideoSettingsMenu, {
        isOpen: true,
        currentSpeed: 1,
        qualities,
        activeQualityId: 'auto',
        isLooping: false,
        isLiveTranscoding: true,
        canLiveTranscode: true,
        showStatsForNerds: false,
        onClose: vi.fn(),
        onSelectSpeed: vi.fn(),
        onSelectQuality: vi.fn(),
        onToggleLoop: vi.fn(),
        onToggleLiveTranscoding: vi.fn(),
        onToggleStatsForNerds: vi.fn(),
      });

      expect(getByText('Quality')).toBeInTheDocument();
      expect(getByText('Playback speed')).toBeInTheDocument();
      expect(getByText('Live Transcoding')).toBeInTheDocument();
      expect(getByText('Loop video')).toBeInTheDocument();
      expect(getByText('Stats for nerds')).toBeInTheDocument();
    });

    it('navigates to quality submenu and triggers onSelectQuality', async () => {
      const onSelectQuality = vi.fn();
      const qualities = [
        { id: 'auto', label: 'Auto' },
        { id: '1080p', label: '1080p HD' },
      ];

      const { getByText } = render(VideoSettingsMenu, {
        isOpen: true,
        currentSpeed: 1,
        qualities,
        activeQualityId: 'auto',
        isLooping: false,
        isLiveTranscoding: true,
        canLiveTranscode: true,
        showStatsForNerds: false,
        onClose: vi.fn(),
        onSelectSpeed: vi.fn(),
        onSelectQuality,
        onToggleLoop: vi.fn(),
        onToggleLiveTranscoding: vi.fn(),
        onToggleStatsForNerds: vi.fn(),
      });

      // Open Quality submenu
      await fireEvent.click(getByText('Quality'));
      expect(getByText('1080p HD')).toBeInTheDocument();

      // Select 1080p
      await fireEvent.click(getByText('1080p HD'));
      expect(onSelectQuality).toHaveBeenCalledWith(qualities[1]);
    });
  });

  describe('VideoStatsForNerds', () => {
    it('displays video diagnostics accurately', () => {
      const stats = {
        assetId: '12345-67890-test',
        viewport: '1920x1080',
        currentResolution: '1920x1080',
        optimalResolution: '1920x1080',
        droppedFrames: '0 / 1200',
        streamType: 'HLS Live Transcode',
        codecs: 'avc1.640028 / mp4a',
        currentTime: '45.0s',
        duration: '180.0s',
        bufferHealth: '12.5s',
        volume: '100% (unmuted)',
        playbackRate: '1x',
      };

      const onClose = vi.fn();
      const { getByText } = render(VideoStatsForNerds, { stats, onClose });

      expect(getByText('Stats for nerds')).toBeInTheDocument();
      expect(getByText('12345-67890-test')).toBeInTheDocument();
      expect(getByText('HLS Live Transcode')).toBeInTheDocument();
      expect(getByText('12.5s')).toBeInTheDocument();
    });
  });

  describe('VideoFeedbackOverlay', () => {
    it('renders seek feedback badge when seeking', () => {
      const { getByText } = render(VideoFeedbackOverlay, {
        showPlayFlash: false,
        isPaused: false,
        seekFeedback: { direction: 'right', seconds: 10 },
        isSpeedBoostActive: false,
        volumeFeedback: null,
      });

      expect(getByText('+10 seconds')).toBeInTheDocument();
    });

    it('renders 2x speed pill when speed boost is active', () => {
      const { getByText } = render(VideoFeedbackOverlay, {
        showPlayFlash: false,
        isPaused: false,
        seekFeedback: null,
        isSpeedBoostActive: true,
        volumeFeedback: null,
      });

      expect(getByText('Speed')).toBeInTheDocument();
    });
  });

  describe('VideoControlsBar', () => {
    it('renders play button, time display, and triggers actions', async () => {
      const onTogglePlay = vi.fn();
      const onToggleFullscreen = vi.fn();

      const { getByLabelText, getByText } = render(VideoControlsBar, {
        isPaused: true,
        currentTime: 25,
        duration: 100,
        buffered: null,
        volume: 0.8,
        isMuted: false,
        playbackRate: 1,
        fitMode: 'contain',
        isAutoplayNext: true,
        isFullscreen: false,
        isSettingsOpen: false,
        qualities: [{ id: 'auto', label: 'Auto' }],
        activeQualityId: 'auto',
        isLooping: false,
        isLiveTranscoding: true,
        canLiveTranscode: true,
        showStatsForNerds: false,
        onTogglePlay,
        onSeek: vi.fn(),
        onVolumeChange: vi.fn(),
        onToggleMute: vi.fn(),
        onToggleAutoplayNext: vi.fn(),
        onTogglePiP: vi.fn(),
        onToggleFitMode: vi.fn(),
        onToggleSettings: vi.fn(),
        onCloseSettings: vi.fn(),
        onToggleFullscreen,
        onSelectSpeed: vi.fn(),
        onSelectQuality: vi.fn(),
        onToggleLoop: vi.fn(),
        onToggleLiveTranscoding: vi.fn(),
        onToggleStatsForNerds: vi.fn(),
      });

      expect(getByText('0:25 / 1:40')).toBeInTheDocument();

      const playButton = getByLabelText('Play (k)');
      await fireEvent.click(playButton);
      expect(onTogglePlay).toHaveBeenCalledTimes(1);

      const fullscreenButton = getByLabelText('Fullscreen (f)');
      await fireEvent.click(fullscreenButton);
      expect(onToggleFullscreen).toHaveBeenCalledTimes(1);
    });
  });
});
