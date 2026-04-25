import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

class RobotGuide extends StatelessWidget {
  final double size;

  const RobotGuide({super.key, this.size = 130});

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: [
        Container(
          width: size + 26,
          height: size + 26,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [AppColors.electricBlue.withValues(alpha: 0.35), Colors.transparent]),
          ),
        ),
        Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const LinearGradient(colors: [Color(0xFF9A83FF), Color(0xFF5E6CFF)]),
            border: Border.all(color: Colors.white24),
          ),
          child: Center(
            child: Container(
              width: size * 0.54,
              height: size * 0.42,
              decoration: BoxDecoration(
                color: const Color(0xFF1B1445),
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _Eye(),
                  _Eye(),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _Eye extends StatelessWidget {
  const _Eye();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 12,
      height: 12,
      decoration: const BoxDecoration(color: AppColors.neonPink, shape: BoxShape.circle),
    );
  }
}
