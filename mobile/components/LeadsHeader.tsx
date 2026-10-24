import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import ConnectionState from "./ConnectionState";

interface LeadsHeaderProps {
  count: number;
  connected: boolean;
  error?: string;
  onSignOut: () => void;
}

export default function LeadsHeader({ count, connected, error, onSignOut }: LeadsHeaderProps) {
  return (
    <View style={styles.container}>
      <View style={styles.heading}>
        <View>
          <Text style={styles.title}>Leads</Text>
          <Text style={styles.summary}>
            {count} {count === 1 ? "Lead" : "Leads"}
          </Text>
        </View>
        <Pressable accessibilityRole="button" onPress={onSignOut} style={styles.signOutButton}>
          <Text style={styles.signOutText}>Sign out</Text>
        </Pressable>
      </View>
      <ConnectionState connected={connected} message={error} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingTop: 8,
    paddingBottom: 16,
  },
  heading: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    color: "#111827",
  },
  summary: {
    marginTop: 2,
    fontSize: 14,
    color: "#6B7280",
  },
  signOutButton: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#D1D5DB",
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  signOutText: {
    color: "#374151",
    fontSize: 14,
    fontWeight: "600",
  },
});
