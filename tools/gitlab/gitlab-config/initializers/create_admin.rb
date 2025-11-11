begin
  user = User.find_by(username: 'rootadmin')
  if user.nil?
    user = User.create!(
      username: 'rootadmin',
      name: 'Root Admin',
      email: 'rootadmin@example.com',
      password: 'Sup3r@ssw0rd42',
      password_confirmation: 'Sup3r@ssw0rd42',
      admin: true
    )
    user.skip_confirmation!
    user.save!
    puts 'Root admin created successfully.'
  else
    puts 'Root admin already exists.'
  end
rescue => e
  puts "Error creating root admin: #{e.message}"
end
