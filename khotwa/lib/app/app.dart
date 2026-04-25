import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/theme/app_theme.dart';
import '../features/analysis/presentation/viewmodels/analysis_viewmodel.dart';
import '../features/auth/presentation/viewmodels/auth_viewmodel.dart';
import '../features/dashboard/presentation/viewmodels/home_viewmodel.dart';
import '../features/project_idea/presentation/viewmodels/idea_viewmodel.dart';
import 'app_router.dart';

class KhotwaApp extends StatelessWidget {
  const KhotwaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthViewModel()),
        ChangeNotifierProvider(create: (_) => HomeViewModel()),
        ChangeNotifierProvider(create: (_) => IdeaViewModel()),
        ChangeNotifierProvider(create: (_) => AnalysisViewModel()),
      ],
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        title: '????',
        theme: AppTheme.darkTheme,
        initialRoute: AppRouter.splash,
        routes: AppRouter.routes,
      ),
    );
  }
}
