import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/glow_button.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';
import '../viewmodels/auth_viewmodel.dart';

class RegisterScreen extends StatelessWidget {
  const RegisterScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<AuthViewModel>();
    return KhotwaScaffold(
      child: Center(
        child: SingleChildScrollView(
          child: GlassCard(
            child: Column(
              children: [
                const Text('????? ????', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
                const SizedBox(height: 18),
                const TextField(decoration: InputDecoration(labelText: '????? ??????')),
                const SizedBox(height: 10),
                const TextField(decoration: InputDecoration(labelText: '?????? ??????????')),
                const SizedBox(height: 10),
                const TextField(decoration: InputDecoration(labelText: '??? ??????')),
                const SizedBox(height: 10),
                const TextField(obscureText: true, decoration: InputDecoration(labelText: '???? ??????')),
                CheckboxListTile(
                  value: vm.acceptedPrivacy,
                  onChanged: (value) => vm.setPrivacy(value ?? false),
                  title: const Text('????? ??? ????? ????????'),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                ),
                SizedBox(
                  width: double.infinity,
                  child: GlowButton(text: '????? ????', onPressed: () => Navigator.pop(context)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
