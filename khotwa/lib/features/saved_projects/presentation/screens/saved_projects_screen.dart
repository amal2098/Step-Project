import 'package:flutter/material.dart';

import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';

class SavedProjectsScreen extends StatelessWidget {
  const SavedProjectsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final items = List.generate(8, (i) => '????? ${i + 1}');
    return KhotwaScaffold(
      title: '???????? ????????',
      child: GridView.builder(
        itemCount: items.length,
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 0.95,
        ),
        itemBuilder: (_, i) {
          return GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(items[i], style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 6),
                const Text('22 ???? 2026', style: TextStyle(fontSize: 12)),
                const Spacer(),
                const Chip(label: Text('??? ????????')),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Expanded(child: OutlinedButton(onPressed: () {}, child: const Text('???'))),
                    const SizedBox(width: 8),
                    Expanded(child: TextButton(onPressed: () {}, child: const Text('???'))),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
