import 'package:flutter/material.dart';

import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';

class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final items = [
      ('???? ?????', '?? ????? ????? ??????? ?????.', true),
      ('????? ????? ?????', '????? ???? ????? ?????? ?????.', false),
      ('????? ?????', '????? ?????? ???? ??????.', true),
    ];

    return KhotwaScaffold(
      title: '?????????',
      child: ListView.separated(
        itemCount: items.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (_, i) {
          final item = items[i];
          return GlassCard(
            child: ListTile(
              leading: Icon(item.$1.contains('????') ? Icons.auto_awesome : Icons.notifications_active),
              title: Text(item.$1),
              subtitle: Text('${item.$2}\n22 ???? 2026'),
              trailing: item.$3 ? Container(width: 10, height: 10, decoration: const BoxDecoration(color: Colors.pinkAccent, shape: BoxShape.circle)) : null,
            ),
          );
        },
      ),
    );
  }
}
