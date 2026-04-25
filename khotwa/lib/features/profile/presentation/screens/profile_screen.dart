import 'package:flutter/material.dart';

import '../../../../app/app_router.dart';
import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KhotwaScaffold(
      title: '????? ??????',
      actions: [
        IconButton(onPressed: () => Navigator.pushNamed(context, AppRouter.settings), icon: const Icon(Icons.settings)),
      ],
      child: Column(
        children: [
          const CircleAvatar(radius: 50, child: Icon(Icons.person, size: 44)),
          const SizedBox(height: 12),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('????????? ????????', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                const Text('?????: ???? ????'),
                const Text('?????? ??????????: user@khotwa.app'),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(onPressed: () {}, child: const Text('????? ????? ??????')),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
