import 'package:flutter/material.dart';

import '../../../../app/app_router.dart';
import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/glow_button.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KhotwaScaffold(
      child: Center(
        child: SingleChildScrollView(
          child: GlassCard(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('????? ??????', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700)),
                const SizedBox(height: 20),
                const TextField(decoration: InputDecoration(labelText: '?????? ??????????')),
                const SizedBox(height: 12),
                const TextField(obscureText: true, decoration: InputDecoration(labelText: '???? ??????')),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    onPressed: () => Navigator.pushNamed(context, AppRouter.forgotPassword),
                    child: const Text('?????'),
                  ),
                ),
                SizedBox(
                  width: double.infinity,
                  child: GlowButton(
                    text: '????? ??????',
                    onPressed: () => Navigator.pushReplacementNamed(context, AppRouter.dashboard),
                  ),
                ),
                const SizedBox(height: 10),
                TextButton(
                  onPressed: () => Navigator.pushNamed(context, AppRouter.privacyPolicy),
                  child: const Text('????? ????????'),
                ),
                TextButton(
                  onPressed: () => Navigator.pushNamed(context, AppRouter.register),
                  child: const Text('?????'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
