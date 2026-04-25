import 'package:flutter/material.dart';

import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/glow_button.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  bool sent = false;

  @override
  Widget build(BuildContext context) {
    return KhotwaScaffold(
      child: Center(
        child: GlassCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('???? ???? ??????', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
              const SizedBox(height: 14),
              const TextField(decoration: InputDecoration(labelText: '?????? ?????????? ??????')),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: GlowButton(
                  text: '????? ???? ????? ?????',
                  onPressed: () => setState(() => sent = true),
                ),
              ),
              const SizedBox(height: 12),
              Text(sent ? '?? ????? ?????? ?????.' : ' ', style: const TextStyle(color: Colors.greenAccent)),
            ],
          ),
        ),
      ),
    );
  }
}
