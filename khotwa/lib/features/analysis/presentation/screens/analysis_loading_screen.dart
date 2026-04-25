import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../app/app_router.dart';
import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';
import '../../../../core/widgets/robot_guide.dart';
import '../viewmodels/analysis_viewmodel.dart';

class AnalysisLoadingScreen extends StatefulWidget {
  const AnalysisLoadingScreen({super.key});

  @override
  State<AnalysisLoadingScreen> createState() => _AnalysisLoadingScreenState();
}

class _AnalysisLoadingScreenState extends State<AnalysisLoadingScreen> {
  @override
  void initState() {
    super.initState();
    final vm = context.read<AnalysisViewModel>();
    vm.start();
    Timer(const Duration(seconds: 6), () {
      if (mounted) {
        Navigator.pushReplacementNamed(context, AppRouter.feasibility);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<AnalysisViewModel>();
    return KhotwaScaffold(
      child: Center(
        child: GlassCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(
                width: 120,
                height: 120,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(width: 120, height: 120, child: CircularProgressIndicator(strokeWidth: 3)),
                    RobotGuide(size: 82),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              const Text('???? ????? ???? ??????...', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
              const SizedBox(height: 12),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 400),
                child: Text(vm.tips[vm.tipIndex], key: ValueKey(vm.tipIndex)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
