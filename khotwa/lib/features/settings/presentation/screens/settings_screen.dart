import 'package:flutter/material.dart';

import '../../../../app/app_router.dart';
import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    String language = '???????';

    return KhotwaScaffold(
      title: '??????? ????????',
      child: ListView(
        children: [
          GlassCard(
            child: Column(
              children: [
                ListTile(title: const Text('????? ???? ??????'), trailing: const Icon(Icons.chevron_right), onTap: () {}),
                SwitchListTile(value: true, onChanged: (_) {}, title: const Text('??????? ?????????')),
                DropdownButtonFormField<String>(
                  value: language,
                  decoration: const InputDecoration(labelText: '????? ?????'),
                  items: const ['???????', 'English'].map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                  onChanged: (_) {},
                ),
                ListTile(
                  title: const Text('????? ????????'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.pushNamed(context, AppRouter.privacyPolicy),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
