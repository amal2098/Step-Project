import 'package:flutter/material.dart';

import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';

class FeasibilityResultsScreen extends StatelessWidget {
  const FeasibilityResultsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KhotwaScaffold(
      title: '????? ??????',
      child: DefaultTabController(
        length: 3,
        child: Column(
          children: [
            const TabBar(tabs: [Tab(text: '?????'), Tab(text: '?????'), Tab(text: '?????')]),
            const SizedBox(height: 10),
            Expanded(
              child: TabBarView(
                children: [
                  _ResultSection(cards: const ['???? ???????', '??? ????? ??????? ???????', '?????? ???????']),
                  _ResultSection(cards: const ['????? ???????', '????? ???????', '??? ????? ??? 90 ???']),
                  _ResultSection(cards: const ['???? ????? ???????', '??????????? ?????? ????????', '?????? ????? ????']),
                ],
              ),
            ),
            Row(
              children: [
                Expanded(child: OutlinedButton(onPressed: () {}, child: const Text('????? PDF'))),
                const SizedBox(width: 10),
                Expanded(child: ElevatedButton(onPressed: () {}, child: const Text('?????'))),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ResultSection extends StatelessWidget {
  final List<String> cards;

  const _ResultSection({required this.cards});

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: cards.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (_, i) => GlassCard(child: Text(cards[i], style: const TextStyle(fontWeight: FontWeight.w600))),
    );
  }
}
