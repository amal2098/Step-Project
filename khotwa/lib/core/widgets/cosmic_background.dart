import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

class CosmicBackground extends StatelessWidget {
  final Widget child;

  const CosmicBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.bgStart, AppColors.bgMiddle, AppColors.bgEnd],
        ),
      ),
      child: Stack(
        children: [
          const Positioned(top: -80, right: -40, child: _GlowOrb(color: AppColors.neonPink, size: 220)),
          const Positioned(bottom: -120, left: -70, child: _GlowOrb(color: AppColors.electricBlue, size: 260)),
          const Positioned(top: 180, left: 20, child: _GlowRing()),
          const Positioned(bottom: 120, right: 12, child: _GlowRing()),
          child,
        ],
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  final Color color;
  final double size;

  const _GlowOrb({required this.color, required this.size});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(colors: [color.withValues(alpha: 0.35), Colors.transparent]),
      ),
    );
  }
}

class _GlowRing extends StatelessWidget {
  const _GlowRing();

  @override
  Widget build(BuildContext context) {
    return Transform.rotate(
      angle: 0.45,
      child: Container(
        width: 100,
        height: 36,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: AppColors.neonPink.withValues(alpha: 0.75), width: 4),
          boxShadow: [
            BoxShadow(color: AppColors.neonPink.withValues(alpha: 0.45), blurRadius: 22, spreadRadius: 2),
          ],
        ),
      ),
    );
  }
}
