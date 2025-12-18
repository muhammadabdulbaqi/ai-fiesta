"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  getAdminStats,
  getAllSubscriptions,
  addTokens,
  addCredits,
  upgradeSubscription,
  getAdminToken,
  makeUserAdmin,
  deleteUser,
  type AdminStats,
  type Subscription,
} from "@/lib/api"
import { useRouter } from "next/navigation"
import { ArrowLeft, Users, Zap, CreditCard, TrendingUp, Trash2, Shield } from "lucide-react"

export default function AdminPage() {
  const router = useRouter()
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [selectedUser, setSelectedUser] = useState<string>("")
  const [tokensToAdd, setTokensToAdd] = useState<string>("")
  const [creditsToAdd, setCreditsToAdd] = useState<string>("")
  const [upgradeTier, setUpgradeTier] = useState<string>("pro")

  useEffect(() => {
    // Check admin authentication
    const adminToken = getAdminToken()
    if (!adminToken) {
      router.push("/admin/login")
      return
    }

    const fetchData = async () => {
      try {
        const [statsData, subsData] = await Promise.all([getAdminStats(), getAllSubscriptions()])
        setStats(statsData)
        setSubscriptions(subsData)
        if (subsData.length > 0) {
          setSelectedUser(subsData[0].user_id)
        }
      } catch (err) {
        console.error("Failed to fetch admin data:", err)
        // If 401, redirect to login
        if (err instanceof Error && err.message.includes("401")) {
          router.push("/admin/login")
        }
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [router])

  const refreshSubs = async () => {
    const subs = await getAllSubscriptions()
    setSubscriptions(subs)
    if (!selectedUser && subs.length > 0) setSelectedUser(subs[0].user_id)
  }

  const handleAddTokens = async () => {
    if (!selectedUser || !tokensToAdd) return
    setBusy(true)
    try {
      await addTokens(Number(tokensToAdd), selectedUser)
      await refreshSubs()
      setTokensToAdd("")
      alert("Tokens added successfully")
    } catch (err: any) {
      alert(err.message || "Failed to add tokens")
      console.error("Failed to add tokens", err)
    } finally {
      setBusy(false)
    }
  }

  const handleAddCredits = async () => {
    if (!selectedUser || !creditsToAdd) return
    setBusy(true)
    try {
      await addCredits(Number(creditsToAdd), selectedUser)
      await refreshSubs()
      setCreditsToAdd("")
      alert("Credits added successfully")
    } catch (err: any) {
      alert(err.message || "Failed to add credits")
      console.error("Failed to add credits", err)
    } finally {
      setBusy(false)
    }
  }

  const handleUpgrade = async () => {
    if (!selectedUser || !upgradeTier) return
    setBusy(true)
    try {
      await upgradeSubscription(upgradeTier, selectedUser)
      await refreshSubs()
      alert("Subscription upgraded successfully")
    } catch (err: any) {
      alert(err.message || "Failed to upgrade subscription")
      console.error("Failed to upgrade subscription", err)
    } finally {
      setBusy(false)
    }
  }

  const handleMakeAdmin = async () => {
    if (!selectedUser) return
    if (!confirm(`Make this user an admin? They will have full access to all features.`)) return
    setBusy(true)
    try {
      await makeUserAdmin(selectedUser)
      await refreshSubs()
      alert("User upgraded to admin successfully")
    } catch (err: any) {
      alert(err.message || "Failed to make user admin")
      console.error("Failed to make user admin", err)
    } finally {
      setBusy(false)
    }
  }

  const handleDeleteUser = async (userId: string, userEmail: string) => {
    if (!confirm(`Delete user ${userEmail}? This action cannot be undone.`)) return
    setBusy(true)
    try {
      await deleteUser(userId)
      await refreshSubs()
      if (selectedUser === userId) {
        setSelectedUser("")
      }
      alert("User deleted successfully")
    } catch (err: any) {
      alert(err.message || "Failed to delete user")
      console.error("Failed to delete user", err)
    } finally {
      setBusy(false)
    }
  }

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
          <div className="mb-4 grid gap-3 md:grid-cols-3">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Select user</label>
              <select
                className="border rounded-md px-3 py-2 bg-background"
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
              >
                {subscriptions.map((sub) => (
                  <option key={sub.user_id} value={sub.user_id}>
                    {sub.user_email || sub.user_username || sub.user_id} ({sub.tier_name})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Add tokens</label>
              <div className="flex gap-2">
                <input
                  className="flex-1 border rounded-md px-3 py-2 bg-background"
                  type="number"
                  min="1"
                  value={tokensToAdd}
                  onChange={(e) => setTokensToAdd(e.target.value)}
                  placeholder="e.g. 1000"
                />
                <Button variant="outline" disabled={busy || !tokensToAdd} onClick={handleAddTokens}>
                  Add
                </Button>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Add credits</label>
              <div className="flex gap-2">
                <input
                  className="flex-1 border rounded-md px-3 py-2 bg-background"
                  type="number"
                  min="1"
                  value={creditsToAdd}
                  onChange={(e) => setCreditsToAdd(e.target.value)}
                  placeholder="e.g. 500"
                />
                <Button variant="outline" disabled={busy || !creditsToAdd} onClick={handleAddCredits}>
                  Add
                </Button>
              </div>
            </div>

            <div className="flex flex-col gap-2 md:col-span-3">
              <label className="text-sm font-medium">Upgrade tier</label>
              <div className="flex flex-col md:flex-row gap-2">
                <select
                  className="border rounded-md px-3 py-2 bg-background md:w-48"
                  value={upgradeTier}
                  onChange={(e) => setUpgradeTier(e.target.value)}
                >
                  <option value="free">Free</option>
                  <option value="pro">Pro</option>
                  <option value="enterprise">Enterprise</option>
                  <option value="admin">Admin</option>
                </select>
                <Button variant="outline" disabled={busy} onClick={handleUpgrade}>
                  Upgrade
                </Button>
                <Button 
                  variant="outline" 
                  disabled={busy || !selectedUser} 
                  onClick={handleMakeAdmin}
                  className="gap-2"
                >
                  <Shield className="w-4 h-4" />
                  Make Admin
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Uses existing endpoints: add tokens/credits and tier upgrade are executed immediately.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Tokens Used</TableHead>
                  <TableHead>Credits Used</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subscriptions.map((sub) => (
                  <TableRow key={sub.id}>
                    <TableCell className="font-medium">
                      <div className="flex flex-col">
                        <span>{sub.user_email || sub.user_username || sub.user_id}</span>
                        {sub.user_email && sub.user_username && (
                          <span className="text-xs text-muted-foreground">{sub.user_username}</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="capitalize text-sm font-medium">{sub.tier_name}</div>
                    </TableCell>
                    <TableCell className="text-sm">
                      <div className="flex flex-col">
                        <span className="font-medium">{sub.tokens_used.toLocaleString()}</span>
                        <span className="text-xs text-muted-foreground">/ {sub.tokens_limit.toLocaleString()}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">
                      <div className="flex flex-col">
                        <span className="font-medium">{sub.credits_used.toLocaleString()}</span>
                        <span className="text-xs text-muted-foreground">/ {sub.credits_limit.toLocaleString()}</span>
                      </div>
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
                    <TableCell>
                      {sub.tier_id !== "admin" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteUser(sub.user_id, sub.user_email || sub.user_username || sub.user_id)}
                          disabled={busy}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
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

