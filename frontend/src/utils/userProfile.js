export function normalizeUser(user) {
  if (!user) {
    return null
  }

  const profile = user.profile ?? {}

  return {
    ...user,
    bio: user.bio ?? profile.bio ?? '',
    profile_image_url: user.profile_image_url ?? profile.profile_image_url ?? '',
    profile_image_alt: user.profile_image_alt ?? profile.profile_image_alt ?? '',
  }
}
