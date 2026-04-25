import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../app/app_router.dart';
import '../../../../core/widgets/khotwa_scaffold.dart';
import '../../../../core/widgets/robot_guide.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    Timer(const Duration(seconds: 3), () {
      if (mounted) {
        Navigator.pushReplacementNamed(context, AppRouter.login);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return KhotwaScaffold(
      child: Center(
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.4, end: 1),
          duration: const Duration(milliseconds: 900),
          builder: (context, value, child) => Opacity(opacity: value, child: child),
          child: const Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              RobotGuide(size: 170),
              SizedBox(height: 20),
              Text('????', style: TextStyle(fontSize: 40, fontWeight: FontWeight.w800)),
              SizedBox(height: 8),
              Text('?? ????? ???? ??? ?????.', style: TextStyle(fontSize: 17)),
            ],
          ),
        ),
      ),
    );
  }
}
