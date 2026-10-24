import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Lead } from "../types/lead";

interface LeadCardProps {
  lead: Lead;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text
        style={styles.value}
        numberOfLines={1}
        ellipsizeMode="middle"
      >
        {value}
      </Text>
    </View>
  );
}

export default function LeadCard({ lead }: LeadCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{getInitials(lead.fullName)}</Text>
        </View>
        <Text style={styles.name} numberOfLines={1}>
          {lead.fullName}
        </Text>
      </View>

      <View style={styles.divider} />

      <Row label="Email" value={lead.email} />
      <Row label="Phone" value={lead.phone} />
      <Row label="Lead ID" value={lead.id} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    elevation: 2,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
  },
  topRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#E0E7FF",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  avatarText: {
    color: "#4338CA",
    fontWeight: "700",
    fontSize: 14,
  },
  name: {
    flex: 1,
    fontSize: 18,
    fontWeight: "600",
    color: "#111827",
  },
  divider: {
    height: 1,
    backgroundColor: "#F3F4F6",
    marginVertical: 12,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 6,
  },
  label: {
    width: 72,
    fontSize: 13,
    color: "#6B7280",
  },
  value: {
    flex: 1,
    flexShrink: 1,
    fontSize: 14,
    color: "#1F2937",
  },
});
