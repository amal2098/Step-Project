import 'package:flutter/material.dart';

import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/glow_button.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';

class SupportScreen extends StatelessWidget {
  const SupportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KhotwaScaffold(
      title: '????? ?????????',
      child: ListView(
        children: [
          GlassCard(
            child: Column(
              children: [
                const TextField(maxLines: 4, decoration: InputDecoration(labelText: '????? ?????')),
                const SizedBox(height: 12),
                SizedBox(width: double.infinity, child: GlowButton(text: '?????', onPressed: () {})),
              ],
            ),
          ),
          const SizedBox(height: 12),
          GlassCard(
            child: ExpansionPanelList.radio(
              expandedHeaderPadding: EdgeInsets.zero,
              children: const [
                ExpansionPanelRadio(
                  value: 'q1',
                  headerBuilder: _header('??? ???? ????? ?????'),
                  body: ListTile(title: Text('?? ???? ???????? ???? "???? ????" ?? ???? ??????.')),
                ),
                ExpansionPanelRadio(
                  value: 'q2',
                  headerBuilder: _header('??? ???? ????????'),
                  body: ListTile(title: Text('??? ?????? ??????? ????? ??? ??????? ?? ???? ???????.')),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

ExpansionPanelHeaderBuilder _header(String title) {
  return (context, isExpanded) => ListTile(title: Text(title));
}
