import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../app/app_router.dart';
import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/glow_button.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';
import '../viewmodels/idea_viewmodel.dart';

class ProjectIdeaScreen extends StatelessWidget {
  const ProjectIdeaScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<IdeaViewModel>();

    return KhotwaScaffold(
      title: '????? ???? ???????',
      child: SingleChildScrollView(
        child: GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const TextField(decoration: InputDecoration(labelText: '??? ???????')),
              const SizedBox(height: 10),
              const TextField(maxLines: 5, decoration: InputDecoration(labelText: '??? ??????')),
              const SizedBox(height: 10),
              DropdownButtonFormField<String>(
                value: vm.industry,
                decoration: const InputDecoration(labelText: '???????'),
                items: vm.industries.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                onChanged: vm.setIndustry,
              ),
              const SizedBox(height: 10),
              DropdownButtonFormField<String>(
                value: vm.audience,
                decoration: const InputDecoration(labelText: '??????? ????????'),
                items: vm.audiences.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                onChanged: vm.setAudience,
              ),
              const SizedBox(height: 16),
              Text('???? ??? ?????: ${vm.capital.toStringAsFixed(0)} ???'),
              Slider(value: vm.capital, min: 5, max: 250, onChanged: vm.setCapital),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: GlowButton(
                  text: '????? ??????',
                  onPressed: () => Navigator.pushNamed(context, AppRouter.analysis),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
