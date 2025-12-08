"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { getAdminStats, getAllSubscriptions, type AdminStats, type Subscription } from "@/lib/api"
import { ArrowLeft, Users, Zap, CreditCard, TrendingUp } from "lucide-react"

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsData, subsData] = await Promise.all([getAdminStats(), getAllSubscriptions()])
        setStats(statsData)
        setSubscriptions(subsData)
      } catch (err) {
        console.error("Failed to fetch admin data:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-4 h-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-2">🎉 AI Fiesta Admin</h1>
              <p className="text-muted-foreground">Dashboard and management</p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {stats &&
            [
              {
                title: "Total Users",
                value: stats.total_users_with_usage,
                icon: Users,
              },
              {
                title: "API Calls",
                value: stats.total_api_calls_made.toLocaleString(),
                icon: TrendingUp,
              },
              {
                title: "Tokens Used",
                value: (stats.total_tokens_consumed / 1000).toFixed(1) + "K",
                icon: Zap,
              },
              {
                title: "Total Cost",
                value: "$" + stats.total_cost_usd.toFixed(2),
                icon: CreditCard,
              },
            ].map((stat, idx) => {
              const Icon = stat.icon
              return (
                <Card key={idx} className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">{stat.title}</p>
                      <p className="text-2xl font-bold mt-2">{stat.value}</p>
                    </div>
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Icon className="w-6 h-6 text-primary" />
                    </div>
                  </div>
                </Card>
              )
            })}
        </div>

        {/* Provider Usage */}
        {stats && Object.keys(stats.by_provider).length > 0 && (
          <Card className="p-6 mb-8">
            <h2 className="text-lg font-semibold mb-4">Usage by Provider</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(stats.by_provider).map(([provider, data]) => (
                <div key={provider} className="bg-muted/50 rounded-lg p-4">
                  <p className="font-semibold capitalize mb-3">{provider}</p>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Calls:</span>
                      <span className="font-medium">{data.calls}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Tokens:</span>
                      <span className="font-medium">{(data.tokens / 1000).toFixed(1)}K</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Cost:</span>
                      <span className="font-medium">${data.cost.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Users Table */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">Users & Subscriptions</h2>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Tokens Used</TableHead>
                  <TableHead>Credits Used</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subscriptions.map((sub) => (
                  <TableRow key={sub.id}>
                    <TableCell className="font-medium">{sub.user_id}</TableCell>
                    <TableCell>
                      <div className="capitalize text-sm font-medium">{sub.tier_name}</div>
                    </TableCell>
                    <TableCell className="text-sm">
                      {sub.tokens_used.toLocaleString()} / {sub.tokens_limit.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm">
                      {sub.credits_used.toLocaleString()} / {sub.credits_limit.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div
                        className={`text-xs font-semibold px-2 py-1 rounded-full w-fit ${
                          sub.status === "active" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                        }`}
                      >
                        {sub.status}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      </div>
    </div>
  )
}

