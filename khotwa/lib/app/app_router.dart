import 'package:flutter/material.dart';

import '../features/analysis/presentation/screens/analysis_loading_screen.dart';
import '../features/auth/presentation/screens/forgot_password_screen.dart';
import '../features/auth/presentation/screens/login_screen.dart';
import '../features/auth/presentation/screens/register_screen.dart';
import '../features/auth/presentation/screens/splash_screen.dart';
import '../features/dashboard/presentation/screens/dashboard_screen.dart';
import '../features/feasibility/presentation/screens/feasibility_results_screen.dart';
import '../features/inspiration/presentation/screens/inspiration_details_screen.dart';
import '../features/inspiration/presentation/screens/inspiration_projects_screen.dart';
import '../features/notifications/presentation/screens/notifications_screen.dart';
import '../features/privacy/presentation/screens/privacy_policy_screen.dart';
import '../features/profile/presentation/screens/profile_screen.dart';
import '../features/project_idea/presentation/screens/project_idea_screen.dart';
import '../features/saved_projects/presentation/screens/saved_projects_screen.dart';
import '../features/settings/presentation/screens/settings_screen.dart';
import '../features/support/presentation/screens/support_screen.dart';

class AppRouter {
  static const splash = '/';
  static const login = '/login';
  static const register = '/register';
  static const forgotPassword = '/forgot-password';
  static const dashboard = '/dashboard';
  static const projectIdea = '/project-idea';
  static const analysis = '/analysis';
  static const feasibility = '/feasibility';
  static const savedProjects = '/saved-projects';
  static const inspiration = '/inspiration';
  static const inspirationDetails = '/inspiration-details';
  static const notifications = '/notifications';
  static const profile = '/profile';
  static const settings = '/settings';
  static const privacyPolicy = '/privacy-policy';
  static const support = '/support';

  static final Map<String, WidgetBuilder> routes = {
    splash: (_) => const SplashScreen(),
    login: (_) => const LoginScreen(),
    register: (_) => const RegisterScreen(),
    forgotPassword: (_) => const ForgotPasswordScreen(),
    dashboard: (_) => const DashboardScreen(),
    projectIdea: (_) => const ProjectIdeaScreen(),
    analysis: (_) => const AnalysisLoadingScreen(),
    feasibility: (_) => const FeasibilityResultsScreen(),
    savedProjects: (_) => const SavedProjectsScreen(),
    inspiration: (_) => const InspirationProjectsScreen(),
    inspirationDetails: (_) => const InspirationDetailsScreen(),
    notifications: (_) => const NotificationsScreen(),
    profile: (_) => const ProfileScreen(),
    settings: (_) => const SettingsScreen(),
    privacyPolicy: (_) => const PrivacyPolicyScreen(),
    support: (_) => const SupportScreen(),
  };
}
