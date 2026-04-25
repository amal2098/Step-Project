import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../app/app_router.dart';
import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/glow_button.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';
import '../../../../core/widgets/robot_guide.dart';
import '../viewmodels/home_viewmodel.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<HomeViewModel>();

    return KhotwaScaffold(
      child: Column(
        children: [
          Expanded(
            child: ListView(
              children: [
                Row(
                  children: [
                    const CircleAvatar(radius: 22, child: Icon(Icons.person)),
                    const SizedBox(width: 12),
                    Text('??????? ????!', style: Theme.of(context).textTheme.titleLarge),
                  ],
                ),
                const SizedBox(height: 14),
                const TextField(decoration: InputDecoration(prefixIcon: Icon(Icons.search), hintText: '???? ?? ?????...')),
                const SizedBox(height: 14),
                GlassCard(
                  child: Row(
                    children: [
                      const RobotGuide(size: 92),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('???? ????? ???? ?????.', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                            const SizedBox(height: 10),
                            GlowButton(
                              text: '???? ????',
                              onPressed: () => Navigator.pushNamed(context, AppRouter.projectIdea),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                const Text('??????? ????????', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                const SizedBox(height: 10),
                SizedBox(
                  height: 100,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: vm.savedProjects.length,
                    separatorBuilder: (_, _) => const SizedBox(width: 10),
                    itemBuilder: (_, i) => SizedBox(width: 210, child: GlassCard(child: Center(child: Text(vm.savedProjects[i])))),
                  ),
                ),
                const SizedBox(height: 14),
                const Text('?????? ????? ?????', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                const SizedBox(height: 10),
                SizedBox(
                  height: 100,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: vm.inspirationProjects.length,
                    separatorBuilder: (_, _) => const SizedBox(width: 10),
                    itemBuilder: (_, i) => SizedBox(width: 210, child: GlassCard(child: Center(child: Text(vm.inspirationProjects[i])))),
                  ),
                ),
              ],
            ),
          ),
          _BottomNav(
            index: vm.navIndex,
            onTap: (index) {
              vm.setIndex(index);
              if (index == 1) Navigator.pushNamed(context, AppRouter.savedProjects);
              if (index == 2) Navigator.pushNamed(context, AppRouter.notifications);
              if (index == 3) Navigator.pushNamed(context, AppRouter.profile);
            },
          ),
        ],
      ),
    );
  }
}

class _BottomNav extends StatelessWidget {
  final int index;
  final ValueChanged<int> onTap;

  const _BottomNav({required this.index, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: BottomNavigationBar(
        currentIndex: index,
        onTap: onTap,
        backgroundColor: Colors.transparent,
        elevation: 0,
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home_rounded), label: '????????'),
          BottomNavigationBarItem(icon: Icon(Icons.folder_rounded), label: '????????'),
          BottomNavigationBarItem(icon: Icon(Icons.notifications_rounded), label: '?????????'),
          BottomNavigationBarItem(icon: Icon(Icons.person_rounded), label: '????? ??????'),
        ],
      ),
    );
  }
}
