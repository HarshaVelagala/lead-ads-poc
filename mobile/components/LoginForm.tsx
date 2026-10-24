import React, { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

interface LoginFormProps {
  error?: string;
  isLoading: boolean;
  onLogin: (email: string, password: string) => Promise<void>;
}

export default function LoginForm({ error, isLoading, onLogin }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.card}>
        <Text style={styles.eyebrow}>HARSHA VELAGALA</Text>
        <Text style={styles.title}>Lead Ads Monitor</Text>
        <Text style={styles.subtitle}>Sign in to view your lead submissions.</Text>
        <Text style={styles.label}>Email</Text>
        <TextInput
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          onChangeText={setEmail}
          placeholder="owner@example.com"
          style={styles.input}
          value={email}
        />
        <Text style={styles.label}>Password</Text>
        <TextInput
          autoComplete="current-password"
          onChangeText={setPassword}
          onSubmitEditing={() => void onLogin(email.trim(), password)}
          placeholder="Enter your password"
          returnKeyType="go"
          secureTextEntry
          style={styles.input}
          value={password}
        />
        {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
        <Pressable
          accessibilityRole="button"
          disabled={isLoading || !email.trim() || !password}
          onPress={() => void onLogin(email.trim(), password)}
          style={({ pressed }) => [
            styles.submitButton,
            (isLoading || !email.trim() || !password) && styles.disabledButton,
            pressed && !isLoading && styles.pressedButton,
          ]}
        >
          {isLoading
            ? <ActivityIndicator color="#FFFFFF" />
            : <Text style={styles.submitText}>Sign in</Text>}
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    justifyContent: "center",
    backgroundColor: "#F9FAFB",
    padding: 20,
  },
  card: {
    width: "100%",
    maxWidth: 440,
    alignSelf: "center",
    padding: 24,
    borderRadius: 16,
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },
  eyebrow: {
    color: "#2563EB",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1,
  },
  title: {
    marginTop: 10,
    color: "#111827",
    fontSize: 26,
    fontWeight: "700",
  },
  subtitle: {
    marginTop: 8,
    marginBottom: 24,
    color: "#6B7280",
    fontSize: 15,
  },
  label: {
    marginBottom: 6,
    color: "#374151",
    fontSize: 14,
    fontWeight: "600",
  },
  input: {
    marginBottom: 16,
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: "#D1D5DB",
    borderRadius: 8,
    color: "#111827",
    fontSize: 16,
  },
  error: {
    marginBottom: 12,
    color: "#B91C1C",
    fontSize: 14,
  },
  submitButton: {
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 4,
    borderRadius: 8,
    backgroundColor: "#2563EB",
  },
  disabledButton: {
    opacity: 0.55,
  },
  pressedButton: {
    opacity: 0.85,
  },
  submitText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
});
