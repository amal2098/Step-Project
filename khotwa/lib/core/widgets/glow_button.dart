import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

class GlowButton extends StatelessWidget {
  final String text;
  final VoidCallback onPressed;

  const GlowButton({super.key, required this.text, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        boxShadow: [
          BoxShadow(color: AppColors.neonPink.withValues(alpha: 0.55), blurRadius: 18),
          BoxShadow(color: AppColors.electricBlue.withValues(alpha: 0.30), blurRadius: 30),
        ],
      ),
      child: ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.neonPink,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
        ),
        child: Text(text, style: const TextStyle(fontWeight: FontWeight.w700)),
      ),
    );
  }
}
