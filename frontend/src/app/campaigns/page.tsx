"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { Campaign, Product } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  draft: "Nháp",
  active: "Đang chạy",
  paused: "Tạm dừng",
  completed: "Hoàn thành",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  active: "bg-green-100 text-green-700",
  paused: "bg-yellow-100 text-yellow-700",
  completed: "bg-blue-100 text-blue-700",
};

const PLATFORM_LABELS: Record<string, string> = {
  shopee: "Shopee",
  tiktok_shop: "TikTok Shop",
  shopback: "ShopBack",
  accesstrade: "AccessTrade VN",
};

export default function CampaignsPage() {
  const queryClient = useQueryClient();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [expandedCampaign, setExpandedCampaign] = useState<string | null>(null);
  const [showProductForm, setShowProductForm] = useState<string | null>(null);

  // Campaign product form state
  const [productForm, setProductForm] = useState({
    name: "", original_url: "", affiliate_url: "", price: "", category: "", description: "",
  });

  const { data: campaigns, isLoading } = useQuery<Campaign[]>({
    queryKey: ["campaigns"],
    queryFn: () => apiFetch("/campaigns"),
  });

  const createCampaignMutation = useMutation({
    mutationFn: (data: { name: string; platform: string; target_category: string }) =>
      apiFetch("/campaigns", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      setShowCreateForm(false);
    },
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/campaigns/${id}/activate`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  const addProductMutation = useMutation({
    mutationFn: ({ campaignId, data }: { campaignId: string; data: object }) =>
      apiFetch(`/campaigns/${campaignId}/products`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: (_, { campaignId }) => {
      queryClient.invalidateQueries({ queryKey: ["products", campaignId] });
      setShowProductForm(null);
      setProductForm({ name: "", original_url: "", affiliate_url: "", price: "", category: "", description: "" });
    },
  });

  const deleteProductMutation = useMutation({
    mutationFn: ({ campaignId, productId }: { campaignId: string; productId: string }) =>
      apiFetch(`/campaigns/${campaignId}/products/${productId}`, { method: "DELETE" }),
    onSuccess: (_, { campaignId }) =>
      queryClient.invalidateQueries({ queryKey: ["products", campaignId] }),
  });

  const handleCreateCampaign = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    createCampaignMutation.mutate({
      name: fd.get("name") as string,
      platform: fd.get("platform") as string,
      target_category: fd.get("category") as string,
    });
  };

  const handleAddProduct = (campaignId: string) => {
    if (!productForm.name || !productForm.original_url) return;
    addProductMutation.mutate({
      campaignId,
      data: {
        name: productForm.name,
        original_url: productForm.original_url,
        affiliate_url: productForm.affiliate_url || null,
        price: productForm.price ? parseFloat(productForm.price) : null,
        category: productForm.category || null,
        description: productForm.description || null,
      },
    });
  };

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Chiến dịch</h1>
        <button
          onClick={() => setShowCreateForm((v) => !v)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          {showCreateForm ? "Hủy" : "+ Tạo chiến dịch"}
        </button>
      </div>

      {/* Create Campaign Form */}
      {showCreateForm && (
        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Tạo chiến dịch mới</h2>
          <form onSubmit={handleCreateCampaign} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tên chiến dịch</label>
              <input
                name="name" required
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
                placeholder="VD: Shopee Thời Trang Q2 2026"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nền tảng</label>
                <select name="platform" required className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none">
                  {Object.entries(PLATFORM_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Danh mục</label>
                <input name="category" className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none" placeholder="VD: thoi_trang, dien_tu" />
              </div>
            </div>
            <button type="submit" disabled={createCampaignMutation.isPending}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium">
              {createCampaignMutation.isPending ? "Đang tạo..." : "Tạo chiến dịch"}
            </button>
          </form>
        </div>
      )}

      {/* Campaign List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="h-20 bg-gray-200 rounded-xl animate-pulse" />)}
        </div>
      ) : campaigns && campaigns.length > 0 ? (
        <div className="space-y-3">
          {campaigns.map((campaign) => (
            <CampaignCard
              key={campaign.id}
              campaign={campaign}
              isExpanded={expandedCampaign === campaign.id}
              onToggle={() => setExpandedCampaign(expandedCampaign === campaign.id ? null : campaign.id)}
              onActivate={() => activateMutation.mutate(campaign.id)}
              showProductForm={showProductForm === campaign.id}
              onToggleProductForm={() => setShowProductForm(showProductForm === campaign.id ? null : campaign.id)}
              productForm={productForm}
              onProductFormChange={(f) => setProductForm((p) => ({ ...p, ...f }))}
              onAddProduct={() => handleAddProduct(campaign.id)}
              onDeleteProduct={(productId) => deleteProductMutation.mutate({ campaignId: campaign.id, productId })}
              isAdding={addProductMutation.isPending && addProductMutation.variables?.campaignId === campaign.id}
              addError={addProductMutation.isError && addProductMutation.variables?.campaignId === campaign.id
                ? (addProductMutation.error as Error).message : null}
            />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center text-gray-400">
          Chưa có chiến dịch nào. Nhấn &quot;+ Tạo chiến dịch&quot; để bắt đầu.
        </div>
      )}
    </div>
  );
}

function CampaignCard({
  campaign, isExpanded, onToggle, onActivate,
  showProductForm, onToggleProductForm,
  productForm, onProductFormChange, onAddProduct, onDeleteProduct,
  isAdding, addError,
}: {
  campaign: Campaign;
  isExpanded: boolean;
  onToggle: () => void;
  onActivate: () => void;
  showProductForm: boolean;
  onToggleProductForm: () => void;
  productForm: Record<string, string>;
  onProductFormChange: (f: Record<string, string>) => void;
  onAddProduct: () => void;
  onDeleteProduct: (id: string) => void;
  isAdding: boolean;
  addError: string | null;
}) {
  const queryClient = useQueryClient();
  const { data: products } = useQuery<Product[]>({
    queryKey: ["products", campaign.id],
    queryFn: () => apiFetch(`/campaigns/${campaign.id}/products`),
    enabled: isExpanded,
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
      {/* Campaign header */}
      <div className="p-5 flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900">{campaign.name}</h3>
          <div className="flex gap-3 mt-1 text-sm text-gray-500">
            <span>{PLATFORM_LABELS[campaign.platform] ?? campaign.platform}</span>
            {campaign.target_category && <span>| {campaign.target_category}</span>}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {campaign.status === "draft" && (
            <button onClick={onActivate}
              className="px-3 py-1 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 transition-colors">
              Kích hoạt
            </button>
          )}
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[campaign.status] ?? STATUS_COLORS.draft}`}>
            {STATUS_LABELS[campaign.status] ?? campaign.status}
          </span>
          <button onClick={onToggle}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors text-sm">
            {isExpanded ? "▲" : "▼"}
          </button>
        </div>
      </div>

      {/* Expanded: Products */}
      {isExpanded && (
        <div className="border-t bg-gray-50 p-5">
          <div className="flex justify-between items-center mb-3">
            <h4 className="text-sm font-semibold text-gray-700">
              Sản phẩm ({products?.length ?? 0})
            </h4>
            <button onClick={onToggleProductForm}
              className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
              {showProductForm ? "✕ Đóng" : "+ Thêm sản phẩm"}
            </button>
          </div>

          {/* Add product form */}
          {showProductForm && (
            <div className="bg-white border rounded-xl p-4 mb-4">
              <h5 className="text-sm font-semibold text-gray-700 mb-3">Thêm sản phẩm mới</h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Tên sản phẩm *</label>
                  <input value={productForm.name} onChange={(e) => onProductFormChange({ name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="VD: Tai nghe Sony WH-1000XM5" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">URL sản phẩm *</label>
                  <input value={productForm.original_url} onChange={(e) => onProductFormChange({ original_url: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="https://shopee.vn/product/..." />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Giá (VNĐ)</label>
                  <input type="number" value={productForm.price} onChange={(e) => onProductFormChange({ price: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="7490000" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Danh mục</label>
                  <input value={productForm.category} onChange={(e) => onProductFormChange({ category: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="Điện tử, Thời trang..." />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Affiliate URL</label>
                  <input value={productForm.affiliate_url} onChange={(e) => onProductFormChange({ affiliate_url: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="https://shp.ee/affiliate/..." />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Mô tả ngắn</label>
                  <input value={productForm.description} onChange={(e) => onProductFormChange({ description: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="Chống ồn, pin 30h..." />
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button onClick={onAddProduct}
                  disabled={!productForm.name || !productForm.original_url || isAdding}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                  {isAdding ? "Đang thêm..." : "Thêm sản phẩm"}
                </button>
                {addError && <p className="text-red-600 text-xs">{addError}</p>}
              </div>
            </div>
          )}

          {/* Product list */}
          {!products || products.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">
              Chưa có sản phẩm. Nhấn &quot;+ Thêm sản phẩm&quot; để thêm thủ công.
            </p>
          ) : (
            <div className="space-y-2">
              {products.map((p) => (
                <div key={p.id} className="bg-white border rounded-lg px-4 py-3 flex items-center justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-800 truncate">{p.name}</p>
                    <div className="flex gap-3 mt-0.5 text-xs text-gray-500">
                      {p.price != null && <span>{Number(p.price).toLocaleString("vi-VN")} ₫</span>}
                      {p.category && <span>| {p.category}</span>}
                      <a href={p.original_url} target="_blank" rel="noopener noreferrer"
                        className="text-blue-500 hover:underline truncate max-w-xs">
                        {p.original_url.length > 40 ? p.original_url.slice(0, 40) + "..." : p.original_url}
                      </a>
                    </div>
                  </div>
                  <button onClick={() => onDeleteProduct(p.id)}
                    className="ml-3 p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors text-sm shrink-0"
                    title="Xóa sản phẩm">
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
