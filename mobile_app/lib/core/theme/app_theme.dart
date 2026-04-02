import 'package:flutter/material.dart';

class AppTheme {
  static const Color primary = Color(0xFF2563EB);
  static const Color secondary = Color(0xFF14B8A6);
  static const Color appBg = Color(0xFFF6F1FB);
  static const Color cardBg = Color(0xFFFCFCFF);
  static const Color mobileSolid = Color(0xFFEEF1F5);
  static const Color mobileInput = Color(0xFFF4F6F9);
  static const Color mobileText = Color(0xFF1F2937);
  static const Color mobileBorder = Color(0x332563EB);
  static const Color muted = Color(0xFF64748B);
  static const Color success = Color(0xFF0EA5A0);
  static const Color danger = Color(0xFFDC2626);

  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, secondary],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static List<BoxShadow> get neoOuter => const [
        BoxShadow(
          color: Color(0x180F172A),
          blurRadius: 18,
          offset: Offset(8, 8),
        ),
        BoxShadow(
          color: Colors.white,
          blurRadius: 18,
          offset: Offset(-8, -8),
        ),
      ];

  static ThemeData theme() {
    final base = ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: appBg,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        primary: primary,
        secondary: secondary,
        surface: cardBg,
      ),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(fontWeight: FontWeight.w800, color: mobileText),
        titleLarge: TextStyle(fontWeight: FontWeight.w700, color: mobileText),
        titleMedium: TextStyle(fontWeight: FontWeight.w700, color: mobileText),
        bodyLarge: TextStyle(color: mobileText),
        bodyMedium: TextStyle(color: mobileText),
      ),
    );

    return base.copyWith(
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: mobileText,
          fontSize: 20,
          fontWeight: FontWeight.w800,
        ),
        iconTheme: IconThemeData(color: mobileText),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: mobileInput,
        hintStyle: const TextStyle(color: muted),
        labelStyle: const TextStyle(color: muted),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(20),
          borderSide: const BorderSide(color: mobileBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(20),
          borderSide: const BorderSide(color: mobileBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(20),
          borderSide: const BorderSide(color: primary, width: 1.4),
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: cardBg,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        margin: EdgeInsets.zero,
      ),
      dividerColor: mobileBorder,
    );
  }

  static ThemeData darkTheme() {
    final base = ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: const Color(0xFF0F172A),
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        brightness: Brightness.dark,
        primary: primary,
        secondary: secondary,
        surface: const Color(0xFF111827),
      ),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(fontWeight: FontWeight.w800, color: Colors.white),
        titleLarge: TextStyle(fontWeight: FontWeight.w700, color: Colors.white),
        titleMedium: TextStyle(fontWeight: FontWeight.w700, color: Colors.white),
        bodyLarge: TextStyle(color: Color(0xFFE5E7EB)),
        bodyMedium: TextStyle(color: Color(0xFFE5E7EB)),
      ),
    );

    return base.copyWith(
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 20,
          fontWeight: FontWeight.w800,
        ),
        iconTheme: IconThemeData(color: Colors.white),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF1F2937),
        hintStyle: const TextStyle(color: Color(0xFF94A3B8)),
        labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(20),
          borderSide: const BorderSide(color: Color(0x33475569)),
        ),
      ),
      dividerColor: const Color(0x33475569),
    );
  }
}
