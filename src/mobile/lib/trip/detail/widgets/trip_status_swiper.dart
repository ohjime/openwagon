import 'package:flutter/material.dart';
import 'package:flutter_swipe_button/flutter_swipe_button.dart';

/// TripStatusSwiper
///
/// A slide-to-act button that cycles through a list of statuses of type [T].
/// - Accepts the current status value (not an index).
/// - Animates the track color on status change.
/// - Animates the label text transition on change.
/// - Calls [onChanged] with the next status after a successful swipe.
class TripStatusSwiper<T> extends StatefulWidget {
  const TripStatusSwiper({
    super.key,
    required this.statuses,
    required this.current,
    required this.onChanged,
    this.labelBuilder,
    this.duration = const Duration(milliseconds: 250),
    this.height = 56,
    this.borderRadius,
    this.padding = const EdgeInsets.symmetric(horizontal: 20),
    this.thumb,
    this.thumbColor,
    this.elevationThumb = 2,
    this.elevationTrack = 0,
    this.trackColorFor,
    this.textColorFor,
  });

  /// Ordered list of statuses to cycle through.
  final List<T> statuses;

  /// The current status value.
  final T current;

  /// Callback with the new status value after a successful swipe.
  final ValueChanged<T> onChanged;

  /// Optional label builder to render a status value as text.
  final String Function(T value)? labelBuilder;

  /// Animation duration for color and text transitions.
  final Duration duration;

  /// Button height.
  final double height;

  /// Optional custom border radius (defaults to 12).
  final BorderRadius? borderRadius;

  /// Outer padding around the button.
  final EdgeInsetsGeometry padding;

  /// Optional custom thumb widget (defaults to a chevron icon).
  final Widget? thumb;

  /// Thumb color when active.
  final Color? thumbColor;

  /// Elevation for thumb.
  final double elevationThumb;

  /// Elevation for track.
  final double elevationTrack;

  /// Optional color resolver for the track based on status value.
  final Color Function(T value)? trackColorFor;

  /// Optional color resolver for the text based on status value.
  final Color Function(T value)? textColorFor;

  @override
  State<TripStatusSwiper<T>> createState() => _TripStatusSwiperState<T>();
}

class _TripStatusSwiperState<T> extends State<TripStatusSwiper<T>>
    with SingleTickerProviderStateMixin {
  late T _current;

  @override
  void initState() {
    super.initState();
    _current = widget.current;
  }

  @override
  void didUpdateWidget(covariant TripStatusSwiper<T> oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.current != widget.current) {
      _current = widget.current;
    }
  }

  int _indexOf(T value) => widget.statuses.indexOf(value);

  Color _defaultTrackColorForIndex(int i) {
    // Simple palette cycling; customize as needed.
    const palette = [
      Color(0xFF607D8B), // blueGrey
      Color(0xFF2196F3), // blue
      Color(0xFFFF9800), // orange
      Color(0xFF4CAF50), // green
      Color(0xFF9C27B0), // purple
      Color(0xFFE91E63), // pink
      Color(0xFF009688), // teal
    ];
    return palette[(i >= 0 ? i : 0) % palette.length];
  }

  Color _defaultTrackColor(T value) {
    final i = _indexOf(value);
    return _defaultTrackColorForIndex(i);
  }

  Color _defaultTextColor(Color bg) {
    // Compute contrast for readability.
    final luminance = bg.computeLuminance();
    return luminance > 0.5 ? Colors.black87 : Colors.white;
  }

  String _defaultLabel(T value) {
    final s = value.toString();
    final pretty = s.contains('.') ? s.split('.').last : s;
    if (pretty.isEmpty) return pretty;
    return pretty[0].toUpperCase() + pretty.substring(1);
  }

  @override
  Widget build(BuildContext context) {
    final radius = widget.borderRadius ?? BorderRadius.circular(12);
    final trackColor =
        (widget.trackColorFor?.call(_current)) ?? _defaultTrackColor(_current);
    final textColor =
        (widget.textColorFor?.call(_current)) ?? _defaultTextColor(trackColor);
    final label =
        (widget.labelBuilder?.call(_current)) ?? _defaultLabel(_current);

    return Padding(
      padding: widget.padding,
      child: TweenAnimationBuilder<Color?>(
        // Animate to the new color whenever the status changes.
        tween: ColorTween(end: trackColor),
        duration: widget.duration,
        builder: (context, color, child) {
          final animatedColor = color ?? trackColor;
          return ClipRRect(
            borderRadius: radius,
            child: Material(
              color: Colors.transparent,
              child: Container(
                decoration: BoxDecoration(
                  color: animatedColor,
                  borderRadius: radius,
                ),
                child: SwipeButton.expand(
                  duration: widget.duration,
                  height: widget.height,
                  elevationThumb: widget.elevationThumb,
                  elevationTrack: widget.elevationTrack,
                  activeTrackColor: animatedColor,
                  activeThumbColor:
                      widget.thumbColor ?? Colors.black.withOpacity(0.25),
                  thumb:
                      widget.thumb ??
                      const Icon(Icons.chevron_right, color: Colors.white),
                  onSwipe: () {
                    if (widget.statuses.isEmpty) return;
                    final currentIndex = _indexOf(_current);
                    final nextIndex = currentIndex < 0
                        ? 0
                        : (currentIndex + 1) % widget.statuses.length;
                    final nextValue = widget.statuses[nextIndex];
                    setState(() => _current = nextValue);
                    widget.onChanged(nextValue);
                  },
                  child: AnimatedSwitcher(
                    duration: widget.duration,
                    transitionBuilder: (child, animation) {
                      final slide =
                          Tween<Offset>(
                            begin: const Offset(0.15, 0),
                            end: Offset.zero,
                          ).animate(
                            CurvedAnimation(
                              parent: animation,
                              curve: Curves.easeOut,
                            ),
                          );
                      return FadeTransition(
                        opacity: animation,
                        child: SlideTransition(position: slide, child: child),
                      );
                    },
                    child: Text(
                      label,
                      key: ValueKey<T>(_current),
                      textAlign: TextAlign.center,
                      style:
                          Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: textColor,
                            fontWeight: FontWeight.w600,
                          ) ??
                          TextStyle(
                            color: textColor,
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
