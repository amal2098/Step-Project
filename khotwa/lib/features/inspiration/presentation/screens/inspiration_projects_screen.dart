import 'package:flutter/material.dart';

import '../../../../app/app_router.dart';
import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';
import '../../../../core/widgets/robot_guide.dart';

class InspirationProjectsScreen extends StatelessWidget {
  const InspirationProjectsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final items = ['???? ?????', '????? ?????', '?????? ?????', '????? ???????'];
    return KhotwaScaffold(
      title: '?????? ???????',
      child: GridView.builder(
        itemCount: items.length,
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 0.82,
        ),
        itemBuilder: (_, i) => InkWell(
          onTap: () => Navigator.pushNamed(context, AppRouter.inspirationDetails),
          child: GlassCard(
            child: Column(
              children: [
                const RobotGuide(size: 72),
                const SizedBox(height: 8),
                Text(items[i], style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 6),
                const Text('????? ??????: 84%', style: TextStyle(fontSize: 12)),
                const Spacer(),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: const [Icon(Icons.favorite_border), Icon(Icons.bookmark_border)],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
