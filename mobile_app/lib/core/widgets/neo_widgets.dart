import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class AppBackdrop extends StatelessWidget {
  const AppBackdrop({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF0F172A) : AppTheme.appBg,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isDark ? const [Color(0xFF0B1020), Color(0xFF111827)] : const [Color(0xFFF8F1FF), Color(0xFFF3FBFF)],
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            top: -40,
            left: -20,
            child: GlowOrb(color: AppTheme.primary.withValues(alpha: .16), size: 160),
          ),
          Positioned(
            right: -30,
            top: 120,
            child: GlowOrb(color: AppTheme.secondary.withValues(alpha: .14), size: 180),
          ),
          SafeArea(child: child),
        ],
      ),
    );
  }
}

class GlowOrb extends StatelessWidget {
  const GlowOrb({super.key, required this.color, required this.size});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
        boxShadow: [
          BoxShadow(color: color, blurRadius: 50, spreadRadius: 10),
        ],
      ),
    );
  }
}

class NeoCard extends StatelessWidget {
  const NeoCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(18),
    this.margin,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      margin: margin,
      padding: padding,
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF111827) : AppTheme.mobileSolid,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: isDark ? const Color(0x33475569) : AppTheme.mobileBorder),
        boxShadow: AppTheme.neoOuter,
      ),
      child: child,
    );
  }
}

class GradientButton extends StatelessWidget {
  const GradientButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.busy = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final Widget? icon;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final disabled = onPressed == null || busy;
    return Opacity(
      opacity: disabled ? .7 : 1,
      child: InkWell(
        onTap: disabled ? null : onPressed,
        borderRadius: BorderRadius.circular(22),
        child: Ink(
          decoration: BoxDecoration(
            gradient: AppTheme.primaryGradient,
            borderRadius: BorderRadius.circular(22),
            boxShadow: [
              BoxShadow(
                color: AppTheme.primary.withValues(alpha: .28),
                blurRadius: 22,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (busy)
                  const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                else if (icon != null) ...[
                  icon!,
                  const SizedBox(width: 8),
                ],
                Text(
                  label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  const SectionTitle({super.key, required this.title, this.subtitle});

  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 28)),
        if (subtitle != null) ...[
          const SizedBox(height: 6),
          Text(subtitle!, style: const TextStyle(color: AppTheme.muted, height: 1.5)),
        ],
      ],
    );
  }
}
